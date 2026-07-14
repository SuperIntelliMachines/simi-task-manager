from datetime import UTC, datetime, timedelta
from dateutil import parser as date_parser

from app.schemas.atm012 import AgentCommandInput


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class FakeLLMProvider:
    """Deterministic in-memory provider for tests; never performs network calls."""

    def __init__(self, fixture_responses: dict[str, dict] | None = None):
        self.fixture_responses = fixture_responses or {}

    def classify_domain(
        self,
        command_text: str,
        candidate_domains: list[str] | None = None,
    ) -> tuple[str | None, float, str | None]:
        text = command_text.lower()

        if "policy renewal" in text or "premium" in text or "claim" in text:
            return "insurance", 0.95, None
        if "wiring" in text or "site" in text or "contractor" in text:
            return "construction", 0.95, None
        if "patient" in text or "clinic" in text or "appointment" in text:
            return "doctors_office", 0.95, None
        if "remind" in text or "call" in text:
            return "general", 0.9, None

        return (
            None,
            0.0,
            "I can help better if you specify whether this is insurance, construction, or doctors office work.",
        )

    def generate_structured_response(self, agent_name: str, command: AgentCommandInput) -> dict:
        text = command.command_text.lower()

        if command.command_text in self.fixture_responses:
            return self.fixture_responses[command.command_text]

        if agent_name == "insurance_agent":
            if "not interested" in text:
                policyholder_name = self._name_after_for(command.command_text) or self._name_after_with(command.command_text) or self._name_after_follow_up(command.command_text)
                return {
                    "domain": "insurance",
                    "intent": "mark_lead_not_interested",
                    "confidence": 0.92,
                    "summary": "Mark the insurance lead as not interested.",
                    "entities": {"policyholder_name": policyholder_name, "summary": "Mark the insurance lead as not interested."},
                    "proposed_actions": [
                        {
                            "tool_name": "mark_lead_not_interested",
                            "args": {"policyholder_name": policyholder_name},
                            "reason": "User said the lead is not interested.",
                        }
                    ],
                    "missing_fields": [] if policyholder_name else ["lead"],
                    "requires_human_approval": False,
                    "clarifying_question": None if policyholder_name else "Which lead should I close?",
                    "user_response": "I marked the lead as not interested." if policyholder_name else None,
                }

            if "follow up later" in text or "reschedule" in text:
                policyholder_name = self._name_after_with(command.command_text) or self._name_after_for(command.command_text)
                followup_at = utcnow_naive() + timedelta(days=7)
                return {
                    "domain": "insurance",
                    "intent": "reschedule_followup",
                    "confidence": 0.91,
                    "summary": "Reschedule an insurance lead follow-up.",
                    "entities": {"policyholder_name": policyholder_name, "followup_at": followup_at.isoformat(), "summary": "Reschedule an insurance lead follow-up."},
                    "proposed_actions": [
                        {
                            "tool_name": "reschedule_followup",
                            "args": {"policyholder_name": policyholder_name, "followup_at": followup_at.isoformat()},
                            "reason": "User requested a later follow-up.",
                        }
                    ],
                    "missing_fields": [] if policyholder_name else ["lead"],
                    "requires_human_approval": False,
                    "clarifying_question": None if policyholder_name else "Which lead should I reschedule?",
                    "user_response": "I rescheduled the follow-up." if policyholder_name else None,
                }

            if "all expiring customers" in text or "bulk" in text:
                return {
                    "domain": "insurance",
                    "intent": "create_premium_reminder",
                    "confidence": 0.96,
                    "summary": "Bulk renewal reminder campaign requires approval.",
                    "entities": {"summary": "Bulk renewal reminder campaign requires approval."},
                    "proposed_actions": [
                        {
                            "tool_name": "create_premium_reminder",
                            "args": {"campaign": "expiring_customers"},
                            "reason": "User requested a bulk reminder campaign.",
                        }
                    ],
                    "missing_fields": [],
                    "requires_human_approval": True,
                    "approval_reason": "Bulk customer reminders require approval.",
                    "clarifying_question": None,
                    "user_response": "This bulk reminder campaign needs approval before I proceed.",
                }

            if text.startswith("renewed") and "policy" in text:
                policyholder_name = command.command_text.replace("Renewed", "").replace("policy", "").replace("'s", "").strip()
                return {
                    "domain": "insurance",
                    "intent": "mark_policy_renewed",
                    "confidence": 0.94,
                    "summary": "Mark a policy as renewed.",
                    "entities": {"policyholder_name": policyholder_name, "summary": "Mark a policy as renewed."},
                    "proposed_actions": [
                        {
                            "tool_name": "mark_policy_renewed",
                            "args": {"policyholder_name": policyholder_name or None},
                            "reason": "User said the policy was renewed.",
                        }
                    ],
                    "missing_fields": [],
                    "requires_human_approval": False,
                    "clarifying_question": None,
                    "user_response": "I marked the policy as renewed.",
                }

            if "after demo" in text or "demo" in text:
                policyholder_name = self._name_after_with(command.command_text) or self._name_after_follow_up(command.command_text)
                followup_at = utcnow_naive() + timedelta(days=3)
                return {
                    "domain": "insurance",
                    "intent": "create_lead_followup",
                    "confidence": 0.93,
                    "summary": "Create a demo follow-up.",
                    "entities": {"policyholder_name": policyholder_name, "followup_at": followup_at.isoformat(), "summary": "Create a demo follow-up."},
                    "proposed_actions": [
                        {
                            "tool_name": "create_lead_followup",
                            "args": {"policyholder_name": policyholder_name, "followup_at": followup_at.isoformat()},
                            "reason": "User requested a demo follow-up.",
                        }
                    ],
                    "missing_fields": [] if policyholder_name else ["policyholder"],
                    "requires_human_approval": False,
                    "clarifying_question": None if policyholder_name else "Who is the demo follow-up for?",
                    "user_response": "I created the demo follow-up." if policyholder_name else None,
                }

            if "create" in text and "policy" in text and ("expiring" in text or " on whatsapp" in text or " on telegram" in text or "auto policy" in text):
                policyholder_name = self._name_after_for(command.command_text)
                expiry_date = self._extract_date(command.command_text)
                preferred_channel = self._extract_channel(text)
                missing_fields = []
                clarifying_question = None
                if expiry_date is None:
                    missing_fields.append("expiry_date")
                    clarifying_question = "When does this policy expire?"
                if not preferred_channel:
                    missing_fields.append("preferred_channel")
                    clarifying_question = clarifying_question or "Which channel should I use for renewal reminders?"
                if policyholder_name and policyholder_name.lower() == "unknown":
                    missing_fields.append("policyholder")
                    clarifying_question = "Please provide contact details for the policyholder."
                policy_type = "auto" if "auto" in text else None
                carrier = "unknown"
                return {
                    "domain": "insurance",
                    "intent": "create_policy_renewal_workflow",
                    "confidence": 0.95,
                    "summary": "Create a policy and renewal workflow.",
                    "entities": {
                        "policyholder_name": policyholder_name,
                        "policy_type": policy_type,
                        "expiry_date": expiry_date.isoformat() if expiry_date else None,
                        "preferred_channel": preferred_channel,
                        "summary": "Create a policy and renewal workflow.",
                    },
                    "proposed_actions": [
                        {
                            "tool_name": "create_policy",
                            "args": {
                                "policyholder_name": policyholder_name,
                                "policy_type": policy_type,
                                "expiry_date": expiry_date.isoformat() if expiry_date else None,
                                "carrier": carrier,
                                "premium_amount": 0,
                                "preferred_channel": preferred_channel,
                            },
                            "reason": "User requested a new insurance policy.",
                        },
                        {
                            "tool_name": "create_policy_renewal_workflow",
                            "args": {
                                "policyholder_name": policyholder_name,
                                "expiry_date": expiry_date.isoformat() if expiry_date else None,
                                "preferred_channel": preferred_channel,
                            },
                            "reason": "New insurance policies need a renewal workflow.",
                        },
                    ],
                    "missing_fields": missing_fields,
                    "requires_human_approval": False,
                    "clarifying_question": clarifying_question,
                    "user_response": "I created the policy and renewal workflow." if not missing_fields else None,
                }

        if agent_name == "insurance_agent" and "policy renewal" in text:
            return {
                "domain": "insurance",
                "intent": "create_lead_followup",
                "confidence": 0.94,
                "summary": "Create a policy renewal follow-up task.",
                "entities": {
                    "policyholder_name": "Ravi",
                    "summary": "Create a policy renewal follow-up task.",
                },
                "proposed_actions": [
                    {
                        "tool_name": "create_lead_followup",
                        "args": {"policyholder_name": "Ravi", "followup_at": self._tomorrow_same_time().isoformat()},
                        "reason": "User requested policy renewal.",
                    }
                ],
                "missing_fields": [],
                "requires_human_approval": False,
                "clarifying_question": None,
                "user_response": "I created a policy renewal follow-up task.",
            }

        if agent_name == "construction_agent" and "wiring" in text:
            return {
                "domain": "construction",
                "intent": "assign_task",
                "confidence": 0.93,
                "summary": "Assign wiring task at Site A to Kumar.",
                "entities": {"site": "Site A", "assignee": "Kumar", "summary": "Assign wiring task at Site A to Kumar."},
                "proposed_actions": [
                    {
                        "tool_name": "assign_task",
                        "args": {
                            "title": "Wiring at Site A",
                            "assignee": "Kumar",
                        },
                        "reason": "User asked to assign wiring work.",
                    }
                ],
                "missing_fields": [],
                "requires_human_approval": False,
                "clarifying_question": None,
                "user_response": "I assigned the wiring task.",
            }

        if agent_name == "doctors_office_agent" and "patient insurance" in text:
            return {
                "domain": "doctors_office",
                "intent": "verify_patient_insurance",
                "confidence": 0.92,
                "summary": "Verify patient insurance for tomorrow.",
                "entities": {"date": "tomorrow", "summary": "Verify patient insurance for tomorrow."},
                "proposed_actions": [
                    {
                        "tool_name": "verify_patient_insurance",
                        "args": {"date": "tomorrow"},
                        "reason": "Insurance verification requested.",
                    }
                ],
                "missing_fields": [],
                "requires_human_approval": False,
                "clarifying_question": None,
                "user_response": "I prepared the insurance verification.",
            }

        if agent_name == "general_task_agent":
            task_id = command.context.get("task_id")
            if "remind me to call" in text:
                target = command.command_text.split("call", 1)[1].split("tomorrow", 1)[0].strip() or "contact"
                scheduled_for = self._next_morning() if "tomorrow morning" in text else self._tomorrow_same_time()
                title = f"Call {target}"
                return {
                    "domain": "general",
                    "intent": "create_reminder",
                    "confidence": 0.95,
                    "summary": f"Create a reminder to call {target}.",
                    "entities": {
                        "title": title,
                        "recipient": target,
                        "due_date": scheduled_for.date().isoformat(),
                        "reminder_time": scheduled_for.isoformat(),
                        "priority": "normal",
                        "summary": f"Create a reminder to call {target}.",
                    },
                    "proposed_actions": [
                        {
                            "tool_name": "create_reminder",
                            "args": {
                                "title": title,
                                "scheduled_for": scheduled_for.isoformat(),
                                "due_at": scheduled_for.isoformat(),
                            },
                            "reason": "User asked for a reminder.",
                        }
                    ],
                    "missing_fields": [],
                    "requires_human_approval": False,
                    "clarifying_question": None,
                    "user_response": f"I created a reminder to call {target}.",
                }

            if text.startswith("assign "):
                remainder = command.command_text[7:].strip()
                assignee_name = None
                title = command.command_text.strip()
                if " to " in remainder:
                    assignee_candidate, task_candidate = remainder.split(" to ", 1)
                    assignee_candidate = assignee_candidate.strip()
                    if assignee_candidate and " " not in assignee_candidate.strip().lower():
                        assignee_name = assignee_candidate
                        title = task_candidate.strip()
                elif remainder.lower().startswith(("the ", "a ", "an ")) or " by " in remainder.lower():
                    title = remainder.strip()
                due_at = self._next_weekday(4) if "friday" in text else None
                if "submit report" in text:
                    title = "Submit report"
                missing_fields = []
                clarifying_question = None
                if not assignee_name:
                    missing_fields.append("assignee")
                    clarifying_question = "Who should I assign this task to?"
                if due_at is None:
                    missing_fields.append("due_date")
                    clarifying_question = clarifying_question or "When is this task due?"
                return {
                    "domain": "general",
                    "intent": "assign_task",
                    "confidence": 0.92,
                    "summary": f"Assign {title.lower()}.",
                    "entities": {
                        "title": title,
                        "assignee": assignee_name,
                        "due_date": due_at.isoformat() if due_at else None,
                        "priority": "normal",
                        "summary": f"Assign {title.lower()}.",
                    },
                    "proposed_actions": [
                        {
                            "tool_name": "assign_task",
                            "args": {
                                "title": title,
                                "assignee_name": assignee_name or None,
                                "due_at": due_at.isoformat() if due_at else None,
                            },
                            "reason": "User asked to assign a task.",
                        }
                    ],
                    "missing_fields": missing_fields,
                    "requires_human_approval": False,
                    "clarifying_question": clarifying_question,
                    "user_response": f"I assigned {title.lower()}." if not missing_fields else None,
                }

            if text.startswith("snooze"):
                due_at = self._next_weekday(0) if "monday" in text else None
                missing_fields = []
                clarifying_question = None
                if task_id is None:
                    missing_fields.append("task")
                    clarifying_question = "Which task should I snooze?"
                if due_at is None:
                    missing_fields.append("due_date")
                    clarifying_question = clarifying_question or "Until when should I snooze it?"
                return {
                    "domain": "general",
                    "intent": "snooze_task",
                    "confidence": 0.9,
                    "summary": "Snooze the active task.",
                    "entities": {"due_date": due_at.isoformat() if due_at else None, "summary": "Snooze the active task."},
                    "proposed_actions": [
                        {
                            "tool_name": "snooze_task",
                            "args": {"task_id": task_id, "due_at": due_at.isoformat() if due_at else None},
                            "reason": "User asked to snooze a task.",
                        }
                    ],
                    "missing_fields": missing_fields,
                    "requires_human_approval": False,
                    "clarifying_question": clarifying_question,
                    "user_response": "I snoozed the task." if not missing_fields else None,
                }

            if text.startswith("complete"):
                title = command.command_text.lower().replace("complete", "", 1).replace("task", "").strip()
                return {
                    "domain": "general",
                    "intent": "complete_task",
                    "confidence": 0.9,
                    "summary": "Complete a task.",
                    "entities": {"title": title, "summary": "Complete a task."},
                    "proposed_actions": [
                        {
                            "tool_name": "complete_task",
                            "args": {"task_id": task_id, "task_title": title or None},
                            "reason": "User asked to complete a task.",
                        }
                    ],
                    "missing_fields": [],
                    "requires_human_approval": False,
                    "clarifying_question": None,
                    "user_response": "I completed the task.",
                }

            if "overdue" in text:
                return {
                    "domain": "general",
                    "intent": "list_overdue_tasks",
                    "confidence": 0.88,
                    "summary": "List overdue tasks.",
                    "entities": {"summary": "List overdue tasks."},
                    "proposed_actions": [
                        {"tool_name": "list_overdue_tasks", "args": {"status": None}, "reason": "User asked for overdue tasks."}
                    ],
                    "missing_fields": [],
                    "requires_human_approval": False,
                    "clarifying_question": None,
                    "user_response": "Here are the overdue tasks.",
                }

            if "summary" in text or "summarize" in text:
                return {
                    "domain": "general",
                    "intent": "summarize_tasks",
                    "confidence": 0.88,
                    "summary": "Summarize tasks.",
                    "entities": {"summary": "Summarize tasks."},
                    "proposed_actions": [
                        {"tool_name": "summarize_tasks", "args": {"status": None}, "reason": "User asked for a task summary."}
                    ],
                    "missing_fields": [],
                    "requires_human_approval": False,
                    "clarifying_question": None,
                    "user_response": "Here is the task summary.",
                }

        return {
            "domain": "general",
            "intent": "create_task",
            "confidence": 0.85,
            "summary": "Create a general follow-up task.",
            "entities": {"summary": "Create a general follow-up task."},
            "proposed_actions": [
                {
                    "tool_name": "create_task",
                    "args": {"title": command.command_text},
                    "reason": "Default deterministic fallback.",
                }
            ],
            "missing_fields": [],
            "requires_human_approval": False,
            "clarifying_question": None,
            "user_response": "I created the task.",
        }

    def _tomorrow_same_time(self) -> datetime:
        return utcnow_naive() + timedelta(days=1)

    def _next_morning(self) -> datetime:
        candidate = utcnow_naive() + timedelta(days=1)
        return candidate.replace(hour=9, minute=0, second=0, microsecond=0)

    def _next_weekday(self, weekday: int) -> datetime:
        candidate = utcnow_naive().replace(hour=9, minute=0, second=0, microsecond=0)
        delta = (weekday - candidate.weekday()) % 7
        delta = 7 if delta == 0 else delta
        return candidate + timedelta(days=delta)

    def _name_after_for(self, text: str) -> str | None:
        lowered = text.lower()
        if " for " not in lowered:
            return None
        fragment = text[lowered.index(" for ") + 5 :]
        for token in [" expiring", " and ", " on "]:
            idx = fragment.lower().find(token)
            if idx != -1:
                fragment = fragment[:idx]
                break
        return fragment.strip() or None

    def _name_after_with(self, text: str) -> str | None:
        lowered = text.lower()
        if " with " not in lowered:
            return None
        fragment = text[lowered.index(" with ") + 6 :]
        for token in [" after", " in "]:
            idx = fragment.lower().find(token)
            if idx != -1:
                fragment = fragment[:idx]
                break
        return fragment.strip() or None

    def _name_after_follow_up(self, text: str) -> str | None:
        lowered = text.lower()
        if "follow up with " not in lowered:
            return None
        fragment = text[lowered.index("follow up with ") + len("follow up with ") :]
        for token in [" after", " in "]:
            idx = fragment.lower().find(token)
            if idx != -1:
                fragment = fragment[:idx]
                break
        return fragment.strip() or None

    def _extract_channel(self, text: str) -> str | None:
        if "whatsapp" in text:
            return "whatsapp"
        if "telegram" in text:
            return "telegram"
        return None

    def _extract_date(self, text: str) -> datetime | None:
        lowered = text.lower()
        if "expiring " not in lowered:
            return None
        fragment = text[lowered.index("expiring ") + len("expiring ") :]
        for token in [" and ", " on "]:
            idx = fragment.lower().find(token)
            if idx != -1:
                fragment = fragment[:idx]
                break
        try:
            return date_parser.parse(fragment, default=utcnow_naive().replace(month=1, day=1))
        except (ValueError, OverflowError):
            return None
