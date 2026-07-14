"""Authentication security: refresh tokens, lockout, audit, password reset, revocation."""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.auth_security import LoginAudit, PasswordResetToken, RefreshToken, RevokedToken
from app.models.core import User

settings = get_settings()
logger = logging.getLogger(__name__)


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _client_meta(request: Request | None) -> tuple[str | None, str | None]:
    if request is None:
        return None, None
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip, user_agent


def validate_password_strength(password: str) -> None:
    """Raise HTTP 400 when password does not meet SIMI strength requirements."""
    value = password or ""
    min_length = settings.min_password_length
    if len(value) < min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {min_length} characters long",
        )
    if value.strip() != value or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot start or end with whitespace",
        )
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must include at least one letter and one number",
        )


class AuthSecurityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_login_rate_limit(self, email: str, request: Request | None = None) -> None:
        ip, _ = _client_meta(request)
        since = utcnow_naive() - timedelta(minutes=1)
        query = select(func.count()).select_from(LoginAudit).where(
            LoginAudit.created_at >= since,
            LoginAudit.email == (email or "").lower(),
        )
        if ip:
            query = query.where(LoginAudit.ip_address == ip)
        count = (await self.session.execute(query)).scalar_one()
        if count >= settings.login_rate_limit_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
            )

    async def assert_account_not_locked(self, user: User) -> None:
        locked_until = getattr(user, "locked_until", None)
        if locked_until is not None and locked_until > utcnow_naive():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is temporarily locked due to repeated failed login attempts.",
            )

    async def record_login_attempt(
        self,
        *,
        email: str,
        success: bool,
        user_id: int | None = None,
        failure_reason: str | None = None,
        request: Request | None = None,
    ) -> None:
        ip, user_agent = _client_meta(request)
        self.session.add(
            LoginAudit(
                user_id=user_id,
                email=(email or "").lower(),
                success=success,
                failure_reason=failure_reason,
                ip_address=ip,
                user_agent=user_agent,
                created_at=utcnow_naive(),
            )
        )

    async def handle_failed_login(self, user: User | None, email: str) -> None:
        if user is None:
            return
        user.failed_login_attempts = int(getattr(user, "failed_login_attempts", 0) or 0) + 1
        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            user.locked_until = utcnow_naive() + timedelta(minutes=settings.account_lockout_minutes)
        user.updated_at = utcnow_naive()

    async def handle_successful_login(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = utcnow_naive()
        user.updated_at = utcnow_naive()

    async def issue_refresh_token(self, user_id: int, request: Request | None = None) -> str:
        raw = secrets.token_urlsafe(48)
        token_hash = _hash_token(raw)
        ip, user_agent = _client_meta(request)
        expires_at = utcnow_naive() + timedelta(days=settings.refresh_token_expire_days)
        self.session.add(
            RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
                user_agent=user_agent,
                ip_address=ip,
                created_at=utcnow_naive(),
            )
        )
        return raw

    async def rotate_refresh_token(self, raw_token: str, request: Request | None = None) -> tuple[str, User]:
        token_hash = _hash_token(raw_token)
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored is None or stored.revoked_at is not None or stored.expires_at <= utcnow_naive():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = await self.session.get(User, stored.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        new_raw = secrets.token_urlsafe(48)
        new_hash = _hash_token(new_raw)
        stored.revoked_at = utcnow_naive()
        stored.replaced_by_token_hash = new_hash
        ip, user_agent = _client_meta(request)
        self.session.add(
            RefreshToken(
                user_id=user.id,
                token_hash=new_hash,
                expires_at=utcnow_naive() + timedelta(days=settings.refresh_token_expire_days),
                user_agent=user_agent,
                ip_address=ip,
                created_at=utcnow_naive(),
            )
        )
        return new_raw, user

    async def revoke_refresh_token(self, raw_token: str) -> None:
        token_hash = _hash_token(raw_token)
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = utcnow_naive()

    async def revoke_all_refresh_tokens(self, user_id: int) -> None:
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        now = utcnow_naive()
        for token in result.scalars().all():
            token.revoked_at = now

    async def revoke_access_token(self, *, jti: str, user_id: int, expires_at: datetime) -> None:
        existing = await self.session.execute(select(RevokedToken).where(RevokedToken.jti == jti))
        if existing.scalar_one_or_none() is not None:
            return
        self.session.add(
            RevokedToken(
                jti=jti,
                user_id=user_id,
                expires_at=expires_at,
                revoked_at=utcnow_naive(),
            )
        )

    async def is_access_token_revoked(self, jti: str | None) -> bool:
        if not jti:
            return False
        result = await self.session.execute(select(RevokedToken.id).where(RevokedToken.jti == jti))
        return result.scalar_one_or_none() is not None

    async def invalidate_unused_password_reset_tokens(self, user_id: int) -> None:
        result = await self.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        now = utcnow_naive()
        for token in result.scalars().all():
            token.used_at = now

    async def create_password_reset_token(self, user: User) -> str:
        await self.invalidate_unused_password_reset_tokens(user.id)
        raw = secrets.token_urlsafe(48)
        token_hash = _hash_token(raw)
        self.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=utcnow_naive() + timedelta(minutes=settings.password_reset_expire_minutes),
                created_at=utcnow_naive(),
            )
        )
        return raw

    def build_password_reset_url(self, raw_token: str) -> str:
        base = settings.frontend_base_url.rstrip("/")
        return f"{base}/reset-password?token={raw_token}"

    async def reset_password_with_token(self, raw_token: str, new_password: str) -> User:
        validate_password_strength(new_password)
        token_hash = _hash_token(raw_token)
        result = await self.session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
        if stored.used_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
        if stored.expires_at <= utcnow_naive():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

        user = await self.session.get(User, stored.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

        user.hashed_password = get_password_hash(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at = utcnow_naive()
        stored.used_at = utcnow_naive()
        await self.revoke_all_refresh_tokens(user.id)
        return user
