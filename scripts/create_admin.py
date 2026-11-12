"""Create the first administrator from environment variables.

Usage:
  $env:BOOTSTRAP_ADMIN_EMAIL="admin@example.com"
  $env:BOOTSTRAP_ADMIN_PASSWORD="a-long-password-1"
  python scripts/create_admin.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User
from app.repositories.store import user_by_email


def main() -> None:
    settings = get_settings()
    email = settings.bootstrap_admin_email.lower().strip()
    password = settings.bootstrap_admin_password
    if not email or len(password) < 12:
        raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and a BOOTSTRAP_ADMIN_PASSWORD of at least 12 characters.")
    db = SessionLocal()
    try:
        existing = user_by_email(db, email)
        if existing:
            print(f"Administrator already exists for {email}")
            return
        db.add(
            User(
                name=settings.bootstrap_admin_name,
                email=email,
                password_hash=hash_password(password),
                role="admin",
                instructor_status="not_applicable",
            )
        )
        db.commit()
        print(f"Created administrator {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
