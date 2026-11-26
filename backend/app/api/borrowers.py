import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import PRIVATE, client_ip, current_user
from app.api.loan_schemas import BorrowerIn, BorrowerOut, BorrowerPatch
from app.db import get_db
from app.models import Borrower, Loan, User
from app.services.audit import record_audit

router = APIRouter(prefix="/api/borrowers", tags=["borrowers"], dependencies=PRIVATE)


def _counts(db: Session, user_id, ids: list) -> dict:
    if not ids:
        return {}
    rows = db.execute(
        select(
            Loan.borrower_id, func.count(Loan.id),
            func.count(Loan.id).filter(Loan.status == "active", Loan.archived_at.is_(None)),
        ).where(Loan.user_id == user_id, Loan.borrower_id.in_(ids)).group_by(Loan.borrower_id)
    ).all()
    return {r[0]: (r[1], r[2]) for r in rows}


def _out(b: Borrower, counts: dict) -> BorrowerOut:
    total, active = counts.get(b.id, (0, 0))
    return BorrowerOut(
        id=b.id, name=b.name, email=b.email, phone=b.phone, notes=b.notes, archived=b.archived_at is not None,
        loan_count=total, active_loan_count=active, created_at=b.created_at,
    )


def _owned(db: Session, user: User, borrower_id: uuid.UUID, lock: bool = False) -> Borrower:
    stmt = select(Borrower).where(Borrower.id == borrower_id, Borrower.user_id == user.id)
    if lock:
        stmt = stmt.with_for_update()
    b = db.scalar(stmt)
    if b is None:
        raise HTTPException(404, "Borrower not found.")
    return b


@router.get("", response_model=list[BorrowerOut])
def list_borrowers(include_archived: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    stmt = select(Borrower).where(Borrower.user_id == user.id).order_by(func.lower(Borrower.name), Borrower.id)
    if not include_archived:
        stmt = stmt.where(Borrower.archived_at.is_(None))
    rows = db.scalars(stmt).all()
    counts = _counts(db, user.id, [b.id for b in rows])
    return [_out(b, counts) for b in rows]


@router.post("", response_model=BorrowerOut, status_code=201)
def create_borrower(
    body: BorrowerIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db),
):
    b = Borrower(user_id=user.id, name=body.name, email=body.email, phone=body.phone, notes=body.notes)
    db.add(b)
    db.flush()
    db.refresh(b)  # loads created_at, which the database fills in
    record_audit(db, "borrower_created", user_id=user.id, ip=client_ip(request), entity_type="borrower", entity_id=str(b.id))
    db.commit()
    return _out(b, {})


@router.patch("/{borrower_id}", response_model=BorrowerOut)
def update_borrower(
    borrower_id: uuid.UUID, body: BorrowerPatch, request: Request,
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    b = _owned(db, user, borrower_id, lock=True)
    sent = body.model_fields_set
    if "name" in sent and body.name is not None:
        b.name = body.name
    for field in ("email", "phone", "notes"):
        if field in sent:
            setattr(b, field, getattr(body, field))
    if "archived" in sent and body.archived is not None:
        if body.archived and b.archived_at is None:
            active = db.scalar(
                select(func.count(Loan.id)).where(
                    Loan.borrower_id == b.id, Loan.user_id == user.id,
                    Loan.status == "active", Loan.archived_at.is_(None),
                )
            )
            if active:
                raise HTTPException(409, "This borrower still has active loans. Close or archive them first.")
            b.archived_at = datetime.now(timezone.utc)
        elif not body.archived:
            b.archived_at = None
    record_audit(
        db, "borrower_updated", user_id=user.id, ip=client_ip(request), entity_type="borrower",
        entity_id=str(b.id), details={"fields": sorted(sent)},
    )
    db.commit()
    return _out(b, _counts(db, user.id, [b.id]))
