"""Telegram insurance workflows delegating to existing domain services."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.telegram.formatting import bullet, empty_state, numbered, section
from app.integrations.telegram.keyboard import MENU_OPEN_PROMPTS
from app.integrations.telegram.parsers import format_followup_date, parse_renewal_date, reminder_channel_to_preferred
from app.integrations.telegram.renewal_context import (
    PendingPolicyRenewal,
    format_invalid_renewal_date_prompt,
    format_renewal_prompt,
    renewal_context_store,
)
from app.models.core import Contact
from app.models.verticals import InsurancePolicy
from app.services.insurance_service import InsuranceService, OPEN_LEAD_STATUSES
from app.services.policy_service import PolicyService
from app.utils.datetime_utils import normalize_to_utc_naive, utcnow_naive
from app.utils.policy_classifier import is_grace_period, is_lapsed

logger = logging.getLogger(__name__)

DEFAULT_RENEWAL_WINDOW_DAYS = 30


class TelegramInsuranceCommandService:
    def __init__(self, session: AsyncSession, *, organization_id: int, actor_user_id: int | None = None):
        self.session = session
        self.organization_id = organization_id
        self.actor_user_id = actor_user_id
        self.insurance = InsuranceService(session)
        self.policy = PolicyService(session)

    async def start_message(self) -> str:
        return (
            "🤖 Welcome to Insurance Assistant Bot.\n"
            "You can manage policies, renewals and follow-ups directly from Telegram."
        )

    async def help_message(self) -> str:
        return (
            f"{MENU_OPEN_PROMPTS['help']}\n\n"
            f"{section('🤖 Insurance Assistant — Commands')}\n\n"
            "/start — Welcome message\n"
            "/help — Show this help\n"
            "/dashboard — Insurance dashboard summary\n"
            "/policies — Policy counts overview\n"
            "/renewals — Upcoming renewals (30 days)\n"
            "/followups — Pending follow-ups\n\n"
            f"{section('💬 Natural Language')}\n"
            "• Create a Health policy for Ravi expiring June 25\n"
            "• Log a follow-up for Priya in 3 days\n"
            "• Log demo for Sanju today and remind me in 3 days\n"
            "• Mark Kumar's policy renewed\n"
            "• Show policies expiring in next 10 days\n"
            "• Show expiring policies in next 5 days\n"
            "• Policies expiring in 15 days\n"
            "• Show active / expiring / expired policies\n"
            "• Show due renewals or pending follow-ups\n"
            "• Show dashboard"
        )

    async def _dashboard_counts(self) -> dict:
        kpis = await self.insurance.get_ui_dashboard_kpis(self.organization_id)
        return {
            "organization_id": kpis["organization_id"],
            "total_policies": kpis["total_policies"],
            "active_policies": kpis["active_policies"],
            "due_renewals": kpis["due_renewals"],
            "expiring_policies": kpis["expiring_policies"],
            "grace_period_policies": kpis["grace_period_policies"],
            "lapsed_policies": kpis["lapsed_policies"],
            "pending_followups": kpis["pending_followups"],
        }

    async def dashboard_summary(self) -> str:
        try:
            stats = await self._dashboard_counts()
            logger.info(
                "telegram /dashboard org=%s total=%s active=%s due=%s expiring=%s grace=%s lapsed=%s followups=%s",
                stats["organization_id"],
                stats["total_policies"],
                stats["active_policies"],
                stats["due_renewals"],
                stats["expiring_policies"],
                stats["grace_period_policies"],
                stats["lapsed_policies"],
                stats["pending_followups"],
            )
            return (
                f"{section('📊 Insurance Dashboard')}\n\n"
                f"{bullet('Total Policies', stats['total_policies'])}\n"
                f"{bullet('Active Policies', stats['active_policies'])}\n"
                f"{bullet('Due Renewals', stats['due_renewals'])}\n"
                f"{bullet('Expiring Policies', stats['expiring_policies'])}\n"
                f"{bullet('Grace Period Policies', stats['grace_period_policies'])}\n"
                f"{bullet('Lapsed Policies', stats['lapsed_policies'])}\n"
                f"{bullet('Pending Follow-ups', stats['pending_followups'])}"
            )
        except Exception as exc:
            logger.exception(
                "telegram /dashboard failed org=%s error_type=%s error=%s",
                self.organization_id,
                type(exc).__name__,
                exc,
            )
            raise

    async def policies_summary(self) -> str:
        try:
            stats = await self._dashboard_counts()
            logger.info(
                "telegram /policies org=%s total=%s active=%s expiring=%s grace=%s lapsed=%s",
                self.organization_id,
                stats["total_policies"],
                stats["active_policies"],
                stats["expiring_policies"],
                stats["grace_period_policies"],
                stats["lapsed_policies"],
            )
            return (
                f"{section('📄 Policy Overview')}\n\n"
                f"{bullet('Total Policies', stats['total_policies'])}\n"
                f"{bullet('Active Policies', stats['active_policies'])}\n"
                f"{bullet('Due Renewals', stats['due_renewals'])}\n"
                f"{bullet('Expiring Policies', stats['expiring_policies'])}\n"
                f"{bullet('Grace Period Policies', stats['grace_period_policies'])}\n"
                f"{bullet('Lapsed Policies', stats['lapsed_policies'])}"
            )
        except Exception as exc:
            logger.exception(
                "telegram /policies failed org=%s error_type=%s error=%s",
                self.organization_id,
                type(exc).__name__,
                exc,
            )
            raise

    async def followups_summary(self) -> str:
        try:
            leads = await self.insurance.list_leads(self.organization_id)
            pending = [
                lead
                for lead in leads
                if lead.status in OPEN_LEAD_STATUSES and lead.followup_due_at is not None
            ]
            pending.sort(key=lambda lead: lead.followup_due_at or utcnow_naive())

            logger.info(
                "telegram /followups org=%s pending_count=%s",
                self.organization_id,
                len(pending),
            )

            if not pending:
                return empty_state("📋 Pending Follow-ups", "No pending follow-ups found.")

            lines = [f"{section('📋 Pending Follow-ups')}\n"]
            for idx, lead in enumerate(pending[:25], start=1):
                name = await self._contact_name(lead.contact_id)
                due = lead.followup_due_at.strftime("%d-%b-%Y") if lead.followup_due_at else "N/A"
                lines.append(numbered(idx, name, f"Due {due}"))
            if len(pending) > 25:
                lines.append(f"\n… and {len(pending) - 25} more")
            return "\n".join(lines)
        except Exception as exc:
            logger.exception(
                "telegram /followups failed org=%s error_type=%s error=%s",
                self.organization_id,
                type(exc).__name__,
                exc,
            )
            raise

    async def expiring_policies_within_days(self, *, days: int) -> str:
        """List active policies expiring within a user-specified day window."""
        try:
            now = utcnow_naive()
            cutoff = now + timedelta(days=days)
            policies = await self.insurance.list_policies(self.organization_id, status="active")
            upcoming = [
                policy
                for policy in policies
                if now <= policy.expiry_date <= cutoff
            ]
            upcoming.sort(key=lambda policy: policy.expiry_date)

            logger.info(
                "Telegram expiring policies query org=%s days_extracted=%s policies_found=%s",
                self.organization_id,
                days,
                len(upcoming),
            )

            if not upcoming:
                response = f"✅ No policies are expiring in the next {days} days."
                logger.info(
                    "Telegram expiring policies response org=%s days=%s response_sent=true empty=true",
                    self.organization_id,
                    days,
                )
                return response

            lines = [f"📅 Policies Expiring in Next {days} Days", ""]
            for policy in upcoming[:25]:
                name = await self._contact_name(policy.policyholder_id)
                days_remaining = max(0, (policy.expiry_date.date() - now.date()).days)
                expiry_label = policy.expiry_date.strftime("%d-%b-%Y")
                lines.extend(
                    [
                        f"Policy: {policy.policy_number}",
                        f"Customer: {name}",
                        f"Expiry Date: {expiry_label}",
                        f"Days Remaining: {days_remaining}",
                        "",
                    ]
                )
            if len(upcoming) > 25:
                lines.append(f"… and {len(upcoming) - 25} more")

            response = "\n".join(lines).rstrip()
            logger.info(
                "Telegram expiring policies response org=%s days=%s policies_found=%s response_sent=true",
                self.organization_id,
                days,
                len(upcoming),
            )
            return response
        except Exception as exc:
            logger.exception(
                "Telegram expiring policies query failed org=%s days=%s error_type=%s error=%s",
                self.organization_id,
                days,
                type(exc).__name__,
                exc,
            )
            raise

    async def renewals_summary(self, *, days: int = DEFAULT_RENEWAL_WINDOW_DAYS) -> str:
        try:
            now = utcnow_naive()
            cutoff = now + timedelta(days=days)
            policies = await self.insurance.list_policies(self.organization_id, status="active")
            upcoming = [
                policy
                for policy in policies
                if now <= policy.expiry_date <= cutoff
            ]
            upcoming.sort(key=lambda policy: policy.expiry_date)

            logger.info(
                "telegram /renewals org=%s window_days=%s count=%s",
                self.organization_id,
                days,
                len(upcoming),
            )

            if not upcoming:
                return empty_state(
                    "📋 Upcoming Renewals",
                    f"No policies expiring in the next {days} days.",
                )

            lines = [f"{section(f'📋 Upcoming Renewals (next {days} days)')}\n"]
            for idx, policy in enumerate(upcoming[:25], start=1):
                name = await self._contact_name(policy.policyholder_id)
                policy_type = policy.policy_type or "General"
                days_remaining = max(0, (policy.expiry_date.date() - now.date()).days)
                expiry_label = policy.expiry_date.strftime("%d-%b-%Y")
                day_label = "day" if days_remaining == 1 else "days"
                lines.append(
                    numbered(
                        idx,
                        name,
                        policy_type,
                        f"{days_remaining} {day_label} left ({expiry_label})",
                    )
                )
            if len(upcoming) > 25:
                lines.append(f"\n… and {len(upcoming) - 25} more")
            return "\n".join(lines)
        except Exception as exc:
            logger.exception(
                "telegram /renewals failed org=%s error_type=%s error=%s",
                self.organization_id,
                type(exc).__name__,
                exc,
            )
            raise

    async def _policy_buckets(self) -> dict[str, list[InsurancePolicy]]:
        """Classify policies using the same windows as the UI dashboard."""
        now = utcnow_naive()
        expiring_cutoff = now + timedelta(days=2)
        due_cutoff = now + timedelta(days=10)
        policies = await self.insurance.list_policies(self.organization_id)

        grace_period: list[InsurancePolicy] = []
        lapsed: list[InsurancePolicy] = []
        active: list[InsurancePolicy] = []

        for policy in policies:
            status = getattr(policy, "status", None)
            if is_lapsed(policy):
                lapsed.append(policy)
            elif is_grace_period(policy):
                grace_period.append(policy)
            else:
                active.append(policy)

        expiring = [p for p in active if now <= p.expiry_date <= expiring_cutoff]
        due = [p for p in active if expiring_cutoff < p.expiry_date <= due_cutoff]

        return {
            "all": policies,
            "active": active,
            "due": due,
            "expiring": expiring,
            "grace_period": grace_period,
            "lapsed": lapsed,
        }

    async def _format_policy_list(
        self,
        *,
        title: str,
        policies: list[InsurancePolicy],
        empty_message: str,
        include_status: bool = False,
    ) -> str:
        if not policies:
            return empty_state(title, empty_message)

        lines = [f"{section(title)}\n"]
        for idx, policy in enumerate(policies[:25], start=1):
            name = await self._contact_name(policy.policyholder_id)
            policy_type = policy.policy_type or "General"
            expiry_label = policy.expiry_date.strftime("%d-%b-%Y")
            detail = f"{policy_type} · Expires {expiry_label}"
            if include_status:
                detail = f"{self._policy_status_label(policy)} · {detail}"
            lines.append(numbered(idx, name, detail))
        if len(policies) > 25:
            lines.append(f"\n… and {len(policies) - 25} more")
        return "\n".join(lines)

    async def policies_total_list(self) -> str:
        buckets = await self._policy_buckets()
        return await self._format_policy_list(
            title="📋 Total Policies",
            policies=sorted(buckets["all"], key=lambda p: p.expiry_date),
            empty_message="No policies found.",
            include_status=True,
        )

    async def policies_active_list(self) -> str:
        buckets = await self._policy_buckets()
        return await self._format_policy_list(
            title="✅ Active Policies",
            policies=sorted(buckets["active"], key=lambda p: p.expiry_date),
            empty_message="No active policies found.",
        )

    async def policies_due_renewals_list(self) -> str:
        buckets = await self._policy_buckets()
        return await self._format_policy_list(
            title="⏰ Due Renewals",
            policies=sorted(buckets["due"], key=lambda p: p.expiry_date),
            empty_message="No policies due for renewal in the next 3–10 days.",
        )

    async def policies_expiring_list(self) -> str:
        buckets = await self._policy_buckets()
        return await self._format_policy_list(
            title="⚠️ Expiring Policies",
            policies=sorted(buckets["expiring"], key=lambda p: p.expiry_date),
            empty_message="No policies expiring in the next 2 days.",
        )

    async def policies_expired_list(self) -> str:
        buckets = await self._policy_buckets()
        return await self._format_policy_list(
            title="❌ Lapsed Policies",
            policies=sorted(buckets["lapsed"], key=lambda p: p.expiry_date, reverse=True),
            empty_message="No lapsed policies found.",
        )

    async def renewals_recently_renewed_list(self) -> str:
        now = utcnow_naive()
        cutoff = now - timedelta(days=30)
        buckets = await self._policy_buckets()
        recently_renewed = [policy for policy in buckets["active"] if policy.updated_at >= cutoff]
        recently_renewed.sort(key=lambda p: p.updated_at, reverse=True)
        seen: set[int] = set()
        unique: list[InsurancePolicy] = []
        for policy in recently_renewed:
            if policy.id in seen:
                continue
            seen.add(policy.id)
            unique.append(policy)

        return await self._format_policy_list(
            title="✅ Recently Renewed",
            policies=unique,
            empty_message="No policies renewed in the last 30 days.",
            include_status=True,
        )

    async def followups_today_summary(self) -> str:
        try:
            now = utcnow_naive()
            today = now.date()
            leads = await self.insurance.list_leads(self.organization_id)
            due_today = [
                lead
                for lead in leads
                if lead.status in OPEN_LEAD_STATUSES
                and lead.followup_due_at is not None
                and lead.followup_due_at.date() == today
            ]
            due_today.sort(key=lambda lead: lead.followup_due_at or now)

            if not due_today:
                return empty_state("📅 Today's Follow-ups", "No follow-ups due today.")

            title = "📅 Today's Follow-ups"
            lines = [f"{section(title)}\n"]
            for idx, lead in enumerate(due_today[:25], start=1):
                name = await self._contact_name(lead.contact_id)
                due = lead.followup_due_at.strftime("%d-%b-%Y") if lead.followup_due_at else "N/A"
                lines.append(numbered(idx, name, f"Due {due}"))
            if len(due_today) > 25:
                lines.append(f"\n… and {len(due_today) - 25} more")
            return "\n".join(lines)
        except Exception as exc:
            logger.exception(
                "telegram followups_today failed org=%s error_type=%s error=%s",
                self.organization_id,
                type(exc).__name__,
                exc,
            )
            raise

    async def followups_create_prompt(self) -> str:
        return (
            "➕ Create Follow-up\n\n"
            "Send a message like:\n"
            "Log a follow-up for Priya in 3 days\n\n"
            "Or log a demo:\n"
            "Log demo for Sanju today and remind me in 3 days"
        )

    async def execute_menu_action(self, action: str) -> str:
        """Run a reply-keyboard menu action."""
        handlers: dict[str, object] = {
            "dashboard.kpi": self.dashboard_summary,
            "dashboard.upcoming_renewals": self.renewals_summary,
            "dashboard.pending_followups": self.followups_summary,
            "policies.total": self.policies_total_list,
            "policies.summary": self.policies_summary,
            "policies.active": self.policies_active_list,
            "policies.due_renewals": self.policies_due_renewals_list,
            "policies.expiring": self.policies_expiring_list,
            "policies.expired": self.policies_expired_list,
            "renewals.due_renewals": self.policies_due_renewals_list,
            "renewals.expiring_10_days": lambda: self.renewals_summary(days=10),
            "renewals.recently_renewed": self.renewals_recently_renewed_list,
            "followups.pending": self.followups_summary,
            "followups.today": self.followups_today_summary,
            "followups.create": self.followups_create_prompt,
            "main.help": self.help_message,
        }
        handler = handlers.get(action)
        if handler is None:
            return "❌ Unknown menu action."
        result = handler()
        if hasattr(result, "__await__"):
            return await result  # type: ignore[misc]
        return result  # type: ignore[return-value]

    async def log_demo(self, *, customer_name: str, followup_days: int) -> str:
        try:
            followup_due_at = utcnow_naive() + timedelta(days=followup_days)
            lead = await self.insurance.create_lead(
                organization_id=self.organization_id,
                contact_name=customer_name,
                actor_user_id=self.actor_user_id,
                source="demo",
                demo_logged_at=utcnow_naive(),
                followup_due_at=followup_due_at,
                status="follow_up_pending",
                notes="Demo logged via Telegram",
            )
            await self.insurance.start_lead_followup_workflow(
                lead_id=lead.id,
                actor_user_id=self.actor_user_id,
                followup_due_at=followup_due_at,
                days_until_followup=followup_days,
            )
            logger.info(
                "telegram demo logged org=%s customer=%s followup_days=%s lead_id=%s",
                self.organization_id,
                customer_name,
                followup_days,
                lead.id,
            )
            return (
                "✅ Demo Logged Successfully\n\n"
                f"Customer: {customer_name}\n"
                f"Follow-up Date: {format_followup_date(followup_days)}"
            )
        except Exception as exc:
            logger.exception(
                "telegram log_demo failed org=%s customer=%s error_type=%s error=%s",
                self.organization_id,
                customer_name,
                type(exc).__name__,
                exc,
            )
            return (
                "❌ Sorry, I couldn't log that demo.\n"
                "Please check the customer name and try again."
            )

    async def log_followup(
        self,
        *,
        customer_name: str,
        followup_days: int,
        notes: str | None = None,
    ) -> str:
        try:
            followup_due_at = utcnow_naive() + timedelta(days=followup_days)
            lead = await self.insurance.create_lead(
                organization_id=self.organization_id,
                contact_name=customer_name,
                actor_user_id=self.actor_user_id,
                source="telegram",
                notes=notes,
                followup_due_at=followup_due_at,
                status="follow_up_pending",
            )
            await self.insurance.start_lead_followup_workflow(
                lead_id=lead.id,
                actor_user_id=self.actor_user_id,
                followup_due_at=followup_due_at,
                days_until_followup=followup_days,
            )
            logger.info(
                "telegram follow-up logged org=%s customer=%s followup_days=%s lead_id=%s",
                self.organization_id,
                customer_name,
                followup_days,
                lead.id,
            )
            due_label = followup_due_at.strftime("%d-%b-%Y")
            lines = [
                "✅ Follow-up Logged Successfully",
                "",
                f"Customer: {customer_name}",
                f"Follow-up Date: {due_label}",
            ]
            if notes:
                lines.append(f"Notes: {notes}")
            return "\n".join(lines)
        except Exception as exc:
            logger.exception(
                "telegram log_followup failed org=%s customer=%s error_type=%s error=%s",
                self.organization_id,
                customer_name,
                type(exc).__name__,
                exc,
            )
            return (
                "❌ Sorry, I couldn't log that follow-up.\n"
                "Please check the customer name and try again."
            )

    async def start_policy_renewal(self, *, customer_name: str, external_user_id: str) -> str:
        logger.info(
            "telegram renew_policy intent customer=%s org=%s user=%s",
            customer_name,
            self.organization_id,
            external_user_id,
        )
        try:
            policy = await self._find_latest_policy_for_customer(customer_name)
            if policy is None:
                logger.info(
                    "telegram renew_policy customer=%s policy_found=false",
                    customer_name,
                )
                return f"❌ No policy found for customer {customer_name}"

            customer = await self._contact_name(policy.policyholder_id)
            previous_status = self._policy_status_label(policy)
            logger.info(
                "telegram renew_policy customer=%s policy_found=true policy_id=%s policy_number=%s status=%s expiry=%s",
                customer_name,
                policy.id,
                policy.policy_number,
                previous_status,
                policy.expiry_date.date().isoformat(),
            )

            if self._is_policy_already_active(policy):
                expiry_label = policy.expiry_date.strftime("%d-%b-%Y")
                logger.info(
                    "telegram renew_policy customer=%s policy_id=%s already_active=true",
                    customer_name,
                    policy.id,
                )
                return (
                    "ℹ️ Policy Already Active\n\n"
                    f"Customer: {customer}\n"
                    f"Policy Number: {policy.policy_number}\n"
                    f"Status: Active\n"
                    f"Expiry Date: {expiry_label}"
                )

            if not self._is_policy_expired_for_renewal(policy):
                return (
                    f"❌ Policy {policy.policy_number} for {customer} is in status "
                    f"{previous_status} and cannot be renewed via Telegram."
                )

            pending = PendingPolicyRenewal(
                external_user_id=external_user_id,
                organization_id=self.organization_id,
                policy_id=policy.id,
                customer_name=customer,
                policy_number=policy.policy_number,
                previous_status=previous_status,
                current_expiry=normalize_to_utc_naive(policy.expiry_date),
            )
            renewal_context_store.set(external_user_id, pending)
            return format_renewal_prompt(pending)
        except Exception as exc:
            logger.exception(
                "telegram renew_policy start failed customer=%s error_type=%s error=%s",
                customer_name,
                type(exc).__name__,
                exc,
            )
            return (
                "❌ Sorry, I couldn't start that policy renewal.\n"
                "Please try again or contact support."
            )

    async def complete_policy_renewal(self, *, external_user_id: str, date_text: str) -> str | None:
        pending = renewal_context_store.get(external_user_id)
        if pending is None:
            return None

        if pending.organization_id != self.organization_id:
            renewal_context_store.clear(external_user_id)
            return None

        new_expiry = parse_renewal_date(date_text)
        if new_expiry is None:
            logger.info(
                "telegram renew_policy invalid_date user=%s customer=%s input=%r",
                external_user_id,
                pending.customer_name,
                date_text,
            )
            return format_invalid_renewal_date_prompt(pending)

        try:
            policy = await self.session.get(InsurancePolicy, pending.policy_id)
            if policy is None:
                renewal_context_store.clear(external_user_id)
                return f"❌ Policy {pending.policy_number} is no longer available."

            new_expiry = normalize_to_utc_naive(new_expiry)
            previous_status = pending.previous_status
            renewal_context_store.clear(external_user_id)

            policy = await self.insurance.mark_policy_renewed(
                policy_id=policy.id,
                actor_user_id=self.actor_user_id,
                new_expiry_date=new_expiry,
            )

            logger.info(
                "telegram renew_policy status_updated user=%s customer=%s policy_id=%s policy_number=%s "
                "previous_status=%s new_status=Renewed new_expiry=%s",
                external_user_id,
                pending.customer_name,
                policy.id,
                policy.policy_number,
                previous_status,
                new_expiry.date().isoformat(),
            )

            return (
                "✅ Policy Renewed\n\n"
                f"Customer: {pending.customer_name}\n"
                f"Policy Number: {policy.policy_number}\n"
                f"Previous Status: {previous_status}\n"
                "New Status: Renewed\n"
                f"New Expiry Date: {new_expiry.strftime('%d-%b-%Y')}"
            )
        except Exception as exc:
            logger.exception(
                "telegram renew_policy complete failed user=%s customer=%s error_type=%s error=%s",
                external_user_id,
                pending.customer_name,
                type(exc).__name__,
                exc,
            )
            return (
                "❌ Sorry, I couldn't renew that policy.\n"
                "Please try again or contact support."
            )

    async def create_policy(
        self,
        *,
        customer_name: str,
        policy_type: str,
        expiry_date,
        reminder_channel: str | None = None,
    ) -> str:
        try:
            preferred_channel = reminder_channel_to_preferred(reminder_channel)
            policy = await self.insurance.create_policy(
                organization_id=self.organization_id,
                policyholder_name=customer_name,
                expiry_date=expiry_date,
                actor_user_id=self.actor_user_id,
                policy_type=policy_type,
                preferred_channel=[preferred_channel] if preferred_channel else None,
            )
            await self.insurance.start_policy_renewal_workflow(
                policy_id=policy.id,
                actor_user_id=self.actor_user_id,
            )
            logger.info(
                "telegram policy created org=%s customer=%s policy_id=%s type=%s reminder_channel=%s",
                self.organization_id,
                customer_name,
                policy.id,
                policy_type,
                reminder_channel,
            )
            expiry_label = expiry_date.strftime("%d-%b-%Y")
            lines = [
                "✅ Policy Created",
                "",
                f"Customer: {customer_name}",
                f"Policy Type: {policy_type}",
                f"Expiry Date: {expiry_label}",
            ]
            if reminder_channel:
                lines.extend(
                    [
                        "",
                        f"📱 Reminder Requested: {reminder_channel}",
                        "(Reminder scheduling will be handled separately)",
                    ]
                )
            return "\n".join(lines)
        except Exception as exc:
            logger.exception(
                "telegram create_policy failed org=%s customer=%s error_type=%s error=%s",
                self.organization_id,
                customer_name,
                type(exc).__name__,
                exc,
            )
            return (
                "❌ Sorry, I couldn't create that policy.\n"
                "Please check the details and try again."
            )

    async def _find_latest_policy_for_customer(self, customer_name: str) -> InsurancePolicy | None:
        needle = customer_name.strip()
        if not needle:
            return None

        contact_result = await self.session.execute(
            select(Contact).where(
                Contact.organization_id == self.organization_id,
                Contact.name.ilike(f"%{needle}%"),
            )
        )
        contacts = list(contact_result.scalars())
        if not contacts:
            return None

        contact_ids = {contact.id for contact in contacts}
        result = await self.session.execute(
            select(InsurancePolicy)
            .where(
                InsurancePolicy.organization_id == self.organization_id,
                InsurancePolicy.policyholder_id.in_(contact_ids),
            )
            .order_by(InsurancePolicy.expiry_date.desc(), InsurancePolicy.created_at.desc())
        )
        policies = list(result.scalars())
        if not policies:
            return None
        if len(policies) > 1 and len(contacts) > 1:
            logger.info(
                "telegram renew_policy multiple policies for customer=%s count=%s using_latest=true",
                customer_name,
                len(policies),
            )
        return policies[0]

    @staticmethod
    def _policy_status_label(policy: InsurancePolicy) -> str:
        if is_lapsed(policy):
            return "Lapsed"
        if is_grace_period(policy):
            return "Grace Period"
        return "Active"

    @staticmethod
    def _is_policy_expired_for_renewal(policy: InsurancePolicy) -> bool:
        return is_lapsed(policy) or is_grace_period(policy)

    @staticmethod
    def _is_policy_already_active(policy: InsurancePolicy) -> bool:
        return not (is_lapsed(policy) or is_grace_period(policy))

    async def _contact_name(self, contact_id: int) -> str:
        contact = await self.session.get(Contact, contact_id)
        if contact is None:
            result = await self.session.execute(select(Contact).where(Contact.id == contact_id))
            contact = result.scalar_one_or_none()
        return contact.name if contact else "Unknown"
