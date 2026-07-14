from datetime import UTC, datetime, timedelta
import uuid

from jose import jwt
from passlib.context import CryptContext
import bcrypt as _bcrypt

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password.

    Attempt direct bcrypt verification using the `bcrypt` library first (works with
    hashes produced by the `bcrypt` package). If that fails, fall back to
    Passlib's `pwd_context.verify` for broader compatibility.
    """
    if not hashed_password:
        return False
    try:
        # bcrypt.checkpw expects bytes
        hp = hashed_password.encode() if isinstance(hashed_password, str) else hashed_password
        # bcrypt limits passwords to 72 bytes; truncate input to same behavior
        pp = plain_password.encode()
        if len(pp) > 72:
            pp = pp[:72]
        return _bcrypt.checkpw(pp, hp)
    except Exception:
        try:
            # Passlib will also be given the truncated password to ensure consistent behavior
            pp = plain_password
            try:
                if isinstance(plain_password, str) and len(plain_password.encode()) > 72:
                    pp = plain_password.encode()[:72].decode(errors="ignore")
            except Exception:
                pp = plain_password
            return pwd_context.verify(pp, hashed_password)
        except Exception:
            return False


def get_password_hash(password: str) -> str:
    # Ensure we never pass >72 bytes to the underlying bcrypt implementation.
    # Use the `bcrypt` library directly on truncated bytes so callers can't
    # accidentally hit the library's length check.
    try:
        pb = password.encode() if isinstance(password, str) else password
        if len(pb) > 72:
            pb = pb[:72]
    except Exception:
        # fallback to original string encoding
        pb = str(password).encode()
    hashed = _bcrypt.hashpw(pb, _bcrypt.gensalt())
    return hashed.decode()


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
