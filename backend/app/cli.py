"""Operator tools that run on your own machine against the real database, never over HTTP.

Run from backend/ with DATABASE_URL set (for example in backend/.env, using the Neon connection string):

    python -m app.cli reset-password you@example.com
    python -m app.cli reset-password you@example.com --activate

This is the way back in if the only administrator forgets their password. It signs the account out
everywhere and writes an audit row.
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.api.schemas import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from app.db import SessionLocal
from app.models import User
from app.services.audit import record_audit
from app.services.passwords import set_password


def reset_password(email: str, activate: bool) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None:
            print("No user with that email.", file=sys.stderr)
            return 1
        password = getpass.getpass("New password: ")
        if password != getpass.getpass("Repeat it: "):
            print("The two entries differ. Nothing was changed.", file=sys.stderr)
            return 1
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            print(
                f"The password must be {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters. Nothing was changed.",
                file=sys.stderr,
            )
            return 1
        revoked = set_password(db, user, password)
        if activate:
            user.is_active = True
        record_audit(
            db, "password_reset_cli", user_id=user.id, entity_type="user", entity_id=str(user.id),
            details={"sessions_revoked": revoked, "activated": activate},
        )
        db.commit()
        print(f"Password updated for {user.email}; {revoked} session(s) signed out.")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    reset = sub.add_parser("reset-password", help="set a new password for an account")
    reset.add_argument("email")
    reset.add_argument("--activate", action="store_true", help="also reactivate a deactivated account")
    args = parser.parse_args(argv)
    return reset_password(args.email, args.activate)


if __name__ == "__main__":
    raise SystemExit(main())
