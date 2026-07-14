#!/usr/bin/env python
"""Check a user's password against the database using the app's models.

Usage:
  python backend/scripts/check_login.py user@example.com password

This script uses the same async DB engine and password verification as the app.
"""
import sys
import asyncio

from sqlalchemy import select, func

# Ensure model modules are imported so SQLAlchemy can resolve relationship targets.
# Importing the package `app.models` will import `core` (which defines Base and primary models).
import app.models  # noqa: F401
import app.models.support_access_sessions  # noqa: F401

from app.core.database import AsyncSessionLocal
from app.models.core import User
from app.core.security import verify_password


async def main(email: str, password: str) -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(func.lower(User.email) == email.lower()))
        user = result.scalars().first()
        if not user:
            print(f"User not found: {email}")
            return 2
        hp = getattr(user, "hashed_password", None)
        print(f"Found user id={user.id} email={user.email} hashed_password_present={bool(hp)}")
        ok = verify_password(password, hp)
        print("Password verification:", "OK" if ok else "FAILED")
        return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python backend/scripts/check_login.py <email> <password>")
        sys.exit(2)
    email = sys.argv[1]
    password = sys.argv[2]
    code = asyncio.run(main(email, password))
    sys.exit(code)
