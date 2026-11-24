from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dashboard_schemas import DashboardSummary
from app.api.deps import PRIVATE, current_user
from app.db import get_db
from app.models import User
from app.services.dashboard import build_summary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"], dependencies=PRIVATE)


@router.get("/summary", response_model=DashboardSummary)
def summary(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return build_summary(db, user)
