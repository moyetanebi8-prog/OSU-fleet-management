#!/usr/bin/env python3
"""
Create an admin account.

This is the ONLY way to create the very first admin account on a fresh
install - after that, an existing admin can create additional
dispatcher/admin accounts via POST /api/v1/admin/accounts/, and employees
via POST /api/v1/admin/employees/. There is no public registration
anywhere in this system.

Usage:
    cd backend
    python scripts/create_admin.py

Run non-interactively with:
    python scripts/create_admin.py --username admin1 --full-name "Admin One" --email admin1@example.com --password "..."
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.auth import hash_password  # noqa: E402


def create_admin_with_session(
    db: Session, username: str, full_name: str, password: str, email: str | None = None
) -> User:
    existing = db.query(User).filter(User.username == username).first()
    if existing is not None:
        raise ValueError(f"Username '{username}' already exists.")

    user = User(
        username=username,
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError(f"Username '{username}' or email '{email}' already exists.") from exc
    db.refresh(user)
    return user


def create_admin(username: str, full_name: str, password: str, email: str | None = None) -> User:
    db = SessionLocal()
    try:
        return create_admin_with_session(db, username, full_name, password, email)
    finally:
        db.close()


def _prompt_for_credentials() -> tuple[str, str, str, str]:
    username = input("Admin username: ").strip()
    full_name = input("Full name: ").strip()
    email = input("Email: ").strip()

    while True:
        password = getpass.getpass("Password (input hidden, min 8 chars): ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match. Try again.\n")
            continue
        if len(password) < 8:
            print("Password must be at least 8 characters. Try again.\n")
            continue
        break

    return username, full_name, email, password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin account.")
    parser.add_argument("--username")
    parser.add_argument("--full-name")
    parser.add_argument("--email")
    parser.add_argument("--password", help="If omitted, you will be prompted (recommended).")
    args = parser.parse_args()

    if args.username and args.full_name and args.email and args.password:
        username, full_name, email, password = args.username, args.full_name, args.email, args.password
    else:
        username, full_name, email, password = _prompt_for_credentials()

    if not username or not full_name or not email:
        print("Username, full name, and email are all required.", file=sys.stderr)
        sys.exit(1)
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    try:
        user = create_admin(username, full_name, password, email)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Admin account created: id={user.id} username={user.username!r} email={user.email!r}")


if __name__ == "__main__":
    main()
