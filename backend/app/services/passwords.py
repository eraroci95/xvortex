from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User, UserSession


def set_password(db: Session, user: User, new_password: str) -> int:
    """Replace the user's password hash and delete all of their sessions, so every device is signed
    out. Returns how many sessions were revoked. The caller audits and commits (and, when the user is
    changing their own password, opens a fresh session afterwards)."""
    user.password_hash = hash_password(new_password)
    return db.execute(delete(UserSession).where(UserSession.user_id == user.id)).rowcount or 0
