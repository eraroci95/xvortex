import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.models import User, UserSettings
from app.services.audit import record_audit

log = logging.getLogger(__name__)


def bootstrap_admin(db: Session, settings: Settings) -> bool:
    """Create the first administrator from ADMIN_EMAIL / ADMIN_PASSWORD when no users exist."""
    if not (settings.admin_email and settings.admin_password):
        return False
    if db.scalar(select(func.count()).select_from(User)):
        return False
    if len(settings.admin_password) < 12:
        log.error("ADMIN_PASSWORD is shorter than 12 characters; admin not created")
        return False
    user = User(
        email=settings.admin_email.strip().lower(),
        password_hash=hash_password(settings.admin_password),
        display_name="Administrator",
        is_admin=True,
    )
    db.add(user)
    db.flush()
    db.add(UserSettings(user_id=user.id))
    record_audit(db, "admin_bootstrapped", user_id=user.id, entity_type="user", entity_id=str(user.id))
    db.commit()
    log.info("bootstrap admin created")
    return True
