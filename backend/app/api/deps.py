from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.enums import UserRole
from app.core.permissions import ADMIN_VIEW, PLATFORM_ROLE_NAMES, USERS_VIEW
from app.core.security import decode_access_token
from app.services.auth_security_service import AuthSecurityService
from app.services.rbac_service import RBACService

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token/swagger")
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token/swagger",
    auto_error=False,
)


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class AuthenticatedUser:
    id: int
    email: str
    role: str
    is_active: bool
    organization_id: int
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has_permission(self, permission: str) -> bool:
        if self.role in PLATFORM_ROLE_NAMES:
            return True
        return permission in self.permissions

    def has_any_permission(self, *permissions: str) -> bool:
        return any(self.has_permission(p) for p in permissions)

    def has_role(self, role: str) -> bool:
        return self.role == role

    def has_any_role(self, *roles: str) -> bool:
        return self.role in set(roles)


async def _load_user_from_db(session: AsyncSession, user_id: int) -> AuthenticatedUser | None:
    result = await session.execute(
        text(
            """
            SELECT id, email, role, is_active, organization_id, locked_until
            FROM users
            WHERE id = :id
            """
        ),
        {"id": user_id},
    )
    row = result.first()
    if not row:
        return None

    locked_until = getattr(row, "locked_until", None)
    if locked_until is not None:
        now = datetime.now(UTC).replace(tzinfo=None)
        if locked_until > now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is temporarily locked due to repeated failed login attempts.",
            )

    rbac = RBACService(session)
    permissions = await rbac.get_permissions_for_role(row.role)
    return AuthenticatedUser(
        id=row.id,
        email=row.email,
        role=row.role,
        is_active=bool(row.is_active),
        organization_id=int(row.organization_id),
        permissions=permissions,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti:
            security = AuthSecurityService(session)
            if await security.is_access_token_revoked(jti):
                raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await _load_user_from_db(session, int(sub))
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


async def get_current_active_admin(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    # RBAC-first admin access: allow explicit platform roles and users who
    # have been granted admin/workspace user-management permissions.
    if current_user.role in {
        UserRole.PLATFORM_ADMIN.value,
        UserRole.SUPPORT_ENGINEER.value,
        UserRole.IMPLEMENTATION_MANAGER.value,
    }:
        return current_user

    if current_user.has_any_permission(ADMIN_VIEW, USERS_VIEW):
        return current_user

    if current_user.role not in PLATFORM_ROLE_NAMES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return current_user


def resolve_organization_scope(current_user: AuthenticatedUser, organization_id: int | None = None) -> int:
    """Return the authenticated user's organization, rejecting cross-tenant access."""
    user_org_id = int(current_user.organization_id)
    if organization_id is not None and int(organization_id) != user_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="cross-tenant access denied")
    return user_org_id


def _forbidden(detail: str = "Forbidden") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_role(role: str) -> Callable:
    async def _dependency(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not current_user.has_role(role):
            raise _forbidden(f"Role '{role}' required")
        return current_user

    return _dependency


def require_any_role(*roles: str) -> Callable:
    async def _dependency(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not current_user.has_any_role(*roles):
            raise _forbidden(f"One of roles {roles} required")
        return current_user

    return _dependency


def require_permission(permission: str) -> Callable:
    async def _dependency(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not current_user.has_permission(permission):
            raise _forbidden(f"Permission '{permission}' required")
        return current_user

    return _dependency


def require_any_permission(*permissions: str) -> Callable:
    async def _dependency(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not current_user.has_any_permission(*permissions):
            raise _forbidden(f"One of permissions {permissions} required")
        return current_user

    return _dependency


class PermissionChecker:
    """Reusable dependency class for route-level permission enforcement."""

    def __init__(self, permission: str):
        self.permission = permission

    async def __call__(self, current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not current_user.has_permission(self.permission):
            raise _forbidden(f"Permission '{self.permission}' required")
        return current_user
