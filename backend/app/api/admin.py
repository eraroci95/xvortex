import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import PRIVATE, client_ip, require_admin
from app.api.schemas import UserActive, UserCreate, UserOut
from app.core.security import hash_password
from app.db import get_db
from app.models import User, UserSession, UserSettings
from app.services.audit import record_audit

# Registration is private: only an administrator can create accounts.
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[*PRIVATE, Depends(require_admin)])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = User(
        email=body.email.strip().lower(), password_hash=hash_password(body.password),
        display_name=body.display_name.strip(), is_admin=body.is_admin,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A user with this email already exists.")
    db.add(UserSettings(user_id=user.id))
    record_audit(db, "user_created", user_id=admin.id, ip=client_ip(request), entity_type="user", entity_id=str(user.id))
    db.commit()
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def set_user_active(
    user_id: uuid.UUID, body: UserActive, request: Request,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "User not found.")
    if user.id == admin.id and not body.is_active:
        raise HTTPException(400, "You cannot deactivate your own account.")
    user.is_active = body.is_active
    if not body.is_active:
        db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    record_audit(
        db, "user_activated" if body.is_active else "user_deactivated",
        user_id=admin.id, ip=client_ip(request), entity_type="user", entity_id=str(user.id),
    )
    db.commit()
    return user
