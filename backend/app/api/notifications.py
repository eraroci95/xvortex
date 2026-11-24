import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.dashboard_schemas import NotificationList
from app.api.deps import PRIVATE, current_user
from app.db import get_db
from app.models import Notification, User
from app.services.dashboard import notification_items, unread_count

router = APIRouter(prefix="/api/notifications", tags=["notifications"], dependencies=PRIVATE)


@router.get("", response_model=NotificationList)
def list_notifications(limit: int = Query(20, ge=1, le=100), user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"unread": unread_count(db, user.id), "items": notification_items(db, user.id, limit)}


@router.post("/read-all", status_code=204)
def read_all(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(
        update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc))
    )
    db.commit()


@router.post("/{notification_id}/read", status_code=204)
def read_one(notification_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if n is None or n.user_id != user.id:  # other users' rows look nonexistent
        raise HTTPException(404, "Notification not found.")
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        db.commit()
