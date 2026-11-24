from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dashboard_schemas import LayoutIO
from app.api.deps import PRIVATE, current_user
from app.db import get_db
from app.models import User, UserSettings
from app.services.dashboard_layout import normalize_layout, validate_layout

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=PRIVATE)


@router.get("/dashboard-layout", response_model=LayoutIO)
def get_layout(user: User = Depends(current_user), db: Session = Depends(get_db)):
    settings = db.get(UserSettings, user.id)
    return {"widgets": normalize_layout(settings.dashboard_layout if settings else None)}


@router.put("/dashboard-layout", response_model=LayoutIO)
def put_layout(body: LayoutIO, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        widgets = validate_layout([w.model_dump() for w in body.widgets])
    except ValueError as e:
        raise HTTPException(422, str(e))
    settings = db.get(UserSettings, user.id)
    if settings is None:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
    settings.dashboard_layout = {"widgets": widgets}
    db.commit()
    return {"widgets": widgets}
