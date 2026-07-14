from datetime import UTC, datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthenticatedUser, get_current_user
from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.core import User
from app.services.auth_security_service import AuthSecurityService, validate_password_strength
from app.services.email_service import EmailDeliveryError, EmailService
from app.seeds.rbac_seed import seed_rbac

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

GENERIC_RESET_DETAIL = "If the account exists, a reset link has been sent."


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str | None = None


class PasswordResetRequestIn(BaseModel):
    email: str


class PasswordResetConfirmIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ChangePasswordOut(BaseModel):
    detail: str


class MeOut(BaseModel):
    id: int
    email: str
    role: str | None = None
    organization_id: int | None = None
    organization_name: str | None = None
    permissions: list[str] = Field(default_factory=list)


class PasswordResetRequestOut(BaseModel):
    detail: str
    reset_token: str | None = None
    reset_url: str | None = None


async def _issue_tokens_for_credentials(
    *,
    email: str,
    password: str,
    request: Request,
    session: AsyncSession,
) -> dict[str, str | None]:
    """Shared login logic for JSON and OAuth2 form token endpoints."""
    await seed_rbac(session)
    security = AuthSecurityService(session)
    normalized_email = (email or "").lower()
    await security.check_login_rate_limit(normalized_email, request)

    result = await session.execute(select(User).where(func.lower(User.email) == normalized_email))
    user = result.scalars().first()

    if user is not None:
        await security.assert_account_not_locked(user)

    if not user or not verify_password(password, getattr(user, "hashed_password", None)):
        await security.record_login_attempt(
            email=normalized_email,
            success=False,
            user_id=getattr(user, "id", None),
            failure_reason="invalid_credentials",
            request=request,
        )
        if user is not None:
            await security.handle_failed_login(user, normalized_email)
            await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not user.is_active:
        await security.record_login_attempt(
            email=normalized_email,
            success=False,
            user_id=user.id,
            failure_reason="inactive_user",
            request=request,
        )
        await session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    await security.handle_successful_login(user)
    await security.record_login_attempt(
        email=normalized_email,
        success=True,
        user_id=user.id,
        request=request,
    )
    refresh_token = await security.issue_refresh_token(user.id, request)
    await session.commit()

    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer", "refresh_token": refresh_token}


@router.post("/token", response_model=TokenOut)
async def login_for_access_token(
    login: LoginIn,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """App/frontend login — JSON body with email + password."""
    return await _issue_tokens_for_credentials(
        email=login.email,
        password=login.password,
        request=request,
        session=session,
    )


@router.post(
    "/token/swagger",
    response_model=TokenOut,
    summary="OAuth2 password login for Swagger Authorize",
    description=(
        "Form-urlencoded OAuth2 password flow used by Swagger UI. "
        "Enter your account email in the username field."
    ),
)
async def login_for_swagger_oauth2(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Swagger Authorize sends application/x-www-form-urlencoded with
    username + password. Map username → email for this API.
    """
    return await _issue_tokens_for_credentials(
        email=form_data.username,
        password=form_data.password,
        request=request,
        session=session,
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh_access_token(
    body: RefreshIn,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    security = AuthSecurityService(session)
    new_refresh, user = await security.rotate_refresh_token(body.refresh_token, request)
    await session.commit()
    access_token = create_access_token(str(user.id))
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh,
    }


@router.post("/logout")
async def logout(
    body: LogoutIn,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    security = AuthSecurityService(session)
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        raw_token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_access_token(raw_token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                expires_at = datetime.fromtimestamp(exp, tz=UTC).replace(tzinfo=None)
                await security.revoke_access_token(
                    jti=jti,
                    user_id=current_user.id,
                    expires_at=expires_at,
                )
        except Exception:
            pass
    if body.refresh_token:
        await security.revoke_refresh_token(body.refresh_token)
    await security.revoke_all_refresh_tokens(current_user.id)
    await session.commit()
    return {"detail": "Logged out successfully"}


@router.post("/logout/revoke")
async def logout_with_access_token(
    body: LogoutIn,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    raw_token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(raw_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    sub = payload.get("sub")
    jti = payload.get("jti")
    exp = payload.get("exp")
    if sub is None or jti is None or exp is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    security = AuthSecurityService(session)
    expires_at = datetime.fromtimestamp(exp, tz=UTC).replace(tzinfo=None)
    await security.revoke_access_token(jti=jti, user_id=int(sub), expires_at=expires_at)
    if body.refresh_token:
        await security.revoke_refresh_token(body.refresh_token)
    await security.revoke_all_refresh_tokens(int(sub))
    await session.commit()
    return {"detail": "Logged out successfully"}


@router.get("/me", response_model=MeOut)
async def read_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    org_name = None
    try:
        if current_user.organization_id:
            result = await session.execute(
                text("SELECT name FROM organizations WHERE id = :id"),
                {"id": int(current_user.organization_id)},
            )
            row = result.first()
            if row:
                org_name = row.name
    except Exception:
        org_name = None
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "organization_id": current_user.organization_id,
        "organization_name": org_name,
        "permissions": sorted(current_user.permissions),
    }


@router.post("/password", response_model=ChangePasswordOut)
async def change_password(
    body: ChangePasswordIn,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    validate_password_strength(body.new_password)
    result = await session.execute(select(User).where(User.id == current_user.id))
    user = result.scalars().first()
    if not user or not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.hashed_password = get_password_hash(body.new_password)
    user.updated_at = datetime.now(UTC).replace(tzinfo=None)
    security = AuthSecurityService(session)
    await security.revoke_all_refresh_tokens(user.id)
    await session.commit()
    return {"detail": "Password updated successfully"}


@router.post("/password-reset/request", response_model=PasswordResetRequestOut)
async def request_password_reset(
    body: PasswordResetRequestIn,
    session: AsyncSession = Depends(get_db_session),
):
    email = (body.email or "").strip().lower()
    result = await session.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalars().first()

    # Always return a generic response in production to avoid email enumeration.
    if user is None or not user.is_active:
        return {"detail": GENERIC_RESET_DETAIL}

    security = AuthSecurityService(session)
    reset_token = await security.create_password_reset_token(user)
    reset_url = security.build_password_reset_url(reset_token)

    if settings.is_production:
        email_service = EmailService.from_settings()
        try:
            await email_service.send_email(
                to=user.email,
                subject="Reset your SIMI password",
                text=(
                    "We received a request to reset your SIMI password.\n\n"
                    f"Open this link to choose a new password (expires in "
                    f"{settings.password_reset_expire_minutes} minutes):\n"
                    f"{reset_url}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                html=(
                    "<p>We received a request to reset your SIMI password.</p>"
                    f"<p><a href=\"{reset_url}\">Reset your password</a></p>"
                    f"<p>This link expires in {settings.password_reset_expire_minutes} minutes.</p>"
                    "<p>If you did not request this, you can ignore this email.</p>"
                ),
            )
        except EmailDeliveryError as exc:
            logger.error("Failed to send password reset email to %s: %s", user.email, exc)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to send password reset email. Please try again later.",
            ) from exc
        await session.commit()
        return {"detail": GENERIC_RESET_DETAIL}

    await session.commit()
    # Development/staging: return token + URL so local testing works without SMTP.
    return {
        "detail": GENERIC_RESET_DETAIL,
        "reset_token": reset_token,
        "reset_url": reset_url,
    }


@router.post("/password-reset/confirm", response_model=ChangePasswordOut)
async def confirm_password_reset(
    body: PasswordResetConfirmIn,
    session: AsyncSession = Depends(get_db_session),
):
    security = AuthSecurityService(session)
    await security.reset_password_with_token(body.token, body.new_password)
    await session.commit()
    return {"detail": "Password reset successfully"}
