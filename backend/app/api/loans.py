import uuid
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import PRIVATE, client_ip, current_user
from app.api.loan_schemas import (
    LoanDetailOut, LoanIn, LoanPatch, LoanSummaryOut, LoanTermsIn, PaymentIn, PaymentOut, PreviewOut,
)
from app.db import get_db
from app.models import Borrower, Loan, LoanPayment, LoanRepaymentSchedule, User
from app.services.audit import record_audit
from app.services.loan_data import (
    figures_for, installment_out, load_facts, summary_fields, summary_out,
)
from app.services.loans.amortization import allocate_payments, build_schedule, money
from app.services.loans.views import assess_all, desired_status, schedule_totals

router = APIRouter(prefix="/api/loans", tags=["loans"], dependencies=PRIVATE)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _schedule_or_422(terms: LoanTermsIn):
    try:
        return build_schedule(
            terms.principal, terms.annual_interest_rate, terms.start_date, terms.maturity_date,
            terms.repayment_frequency, terms.amortization_method,
        )
    except ValueError as exc:  # e.g. too many installments for the chosen period
        raise HTTPException(422, str(exc))


def _owned(db: Session, user: User, loan_id: uuid.UUID, lock: bool = False) -> Loan:
    stmt = select(Loan).where(Loan.id == loan_id, Loan.user_id == user.id)
    if lock:
        stmt = stmt.with_for_update()  # serialises concurrent payment changes on one loan
    loan = db.scalar(stmt)
    if loan is None:
        raise HTTPException(404, "Loan not found.")
    return loan


def _names(db: Session, user: User) -> dict:
    return {b.id: b.name for b in db.scalars(select(Borrower).where(Borrower.user_id == user.id))}


def _detail(db: Session, user: User, loan: Loan) -> LoanDetailOut:
    """Risk is judged against all of the user's open loans in the same currency."""
    today = _today()
    others = list(db.scalars(select(Loan).where(Loan.user_id == user.id)))
    pairs = figures_for(load_facts(db, others), today)
    risks = assess_all(pairs, today)
    fig = next(fig for f, fig in pairs if f.loan_id == loan.id)
    payments = db.scalars(
        select(LoanPayment).where(LoanPayment.loan_id == loan.id).order_by(LoanPayment.paid_on, LoanPayment.created_at)
    ).all()
    name = _names(db, user).get(loan.borrower_id, "")
    return LoanDetailOut(
        **summary_fields(loan, name, fig, risks.get(loan.id)),
        notes=loan.notes, created_at=loan.created_at,
        total_paid=money(sum((p.amount for p in payments), money(0))),
        schedule=[installment_out(a, today) for a in fig.allocations],
        payments=[PaymentOut(id=p.id, paid_on=p.paid_on, amount=p.amount, note=p.note) for p in payments],
    )


@router.post("/preview", response_model=PreviewOut)
def preview(terms: LoanTermsIn):
    schedule = _schedule_or_422(terms)
    allocations, _ = allocate_payments(schedule, [])
    p, i, total = schedule_totals(schedule)
    return PreviewOut(
        installments=[installment_out(a, _today()) for a in allocations],
        total_principal=p, total_interest=i, total_repayable=total,
    )


@router.get("", response_model=list[LoanSummaryOut])
def list_loans(
    view: Literal["active", "finished", "archived", "all"] = "active",
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    today = _today()
    loans = list(db.scalars(select(Loan).where(Loan.user_id == user.id).order_by(Loan.start_date.desc(), Loan.id)))
    pairs = figures_for(load_facts(db, loans), today)
    risks = assess_all(pairs, today)
    names = _names(db, user)
    by_id = {fig_f.loan_id: fig for fig_f, fig in pairs}

    def wanted(loan: Loan) -> bool:
        archived = loan.archived_at is not None
        if view == "all":
            return True
        if view == "archived":
            return archived
        if archived:
            return False
        return loan.status == "active" if view == "active" else loan.status != "active"

    return [
        summary_out(l, names.get(l.borrower_id, ""), by_id[l.id], risks.get(l.id)) for l in loans if wanted(l)
    ]


@router.post("", response_model=LoanDetailOut, status_code=201)
def create_loan(body: LoanIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    borrower = db.scalar(
        select(Borrower).where(Borrower.id == body.borrower_id, Borrower.user_id == user.id).with_for_update()
    )
    if borrower is None:
        raise HTTPException(404, "Borrower not found.")
    if borrower.archived_at is not None:
        raise HTTPException(409, "This borrower is archived. Restore them before adding a loan.")
    schedule = _schedule_or_422(body)
    loan = Loan(
        user_id=user.id, borrower_id=borrower.id, principal=body.principal,
        annual_interest_rate=body.annual_interest_rate, currency=body.currency, start_date=body.start_date,
        maturity_date=body.maturity_date, repayment_frequency=body.repayment_frequency,
        amortization_method=body.amortization_method, notes=body.notes, status="active",
    )
    db.add(loan)
    db.flush()
    db.refresh(loan)
    for i in schedule:
        db.add(LoanRepaymentSchedule(
            loan_id=loan.id, installment_no=i.number, due_date=i.due_date,
            principal_due=i.principal, interest_due=i.interest,
        ))
    record_audit(
        db, "loan_created", user_id=user.id, ip=client_ip(request), entity_type="loan", entity_id=str(loan.id),
        details={"currency": loan.currency, "installments": len(schedule)},
    )
    db.commit()
    return _detail(db, user, loan)


@router.get("/{loan_id}", response_model=LoanDetailOut)
def get_loan(loan_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _detail(db, user, _owned(db, user, loan_id))


def _resync_status(db: Session, loan: Loan) -> None:
    """Move an open loan between active and repaid to match its payments. Closed stays closed."""
    fig = figures_for(load_facts(db, [loan]), _today())[0][1]
    loan.status = desired_status(loan.status, fig)


@router.patch("/{loan_id}", response_model=LoanDetailOut)
def update_loan(
    loan_id: uuid.UUID, body: LoanPatch, request: Request,
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    loan = _owned(db, user, loan_id, lock=True)
    sent = body.model_fields_set
    if "notes" in sent:
        loan.notes = (body.notes or "").strip() or None
    if "status" in sent and body.status is not None:
        if body.status == "closed":
            loan.status = "closed"
        elif loan.status == "closed":
            loan.status = "active"
            db.flush()
            _resync_status(db, loan)  # reopening a fully paid loan makes it repaid, not active
    if "archived" in sent and body.archived is not None:
        if body.archived:
            if loan.status == "active":
                raise HTTPException(409, "Only repaid or closed loans can be archived.")
            loan.archived_at = loan.archived_at or datetime.now(timezone.utc)
        else:
            loan.archived_at = None
    record_audit(
        db, "loan_updated", user_id=user.id, ip=client_ip(request), entity_type="loan", entity_id=str(loan.id),
        details={"fields": sorted(sent), "status": loan.status},
    )
    db.commit()
    return _detail(db, user, loan)


@router.post("/{loan_id}/payments", response_model=LoanDetailOut, status_code=201)
def add_payment(
    loan_id: uuid.UUID, body: PaymentIn, request: Request,
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    loan = _owned(db, user, loan_id, lock=True)
    if loan.status != "active":
        raise HTTPException(409, f"This loan is {loan.status}. Payments can only be added to active loans.")
    if body.paid_on < loan.start_date:
        raise HTTPException(422, "A payment cannot be dated before the loan starts.")
    if body.paid_on > _today():
        raise HTTPException(422, "A payment cannot be dated in the future.")
    payment = LoanPayment(loan_id=loan.id, paid_on=body.paid_on, amount=body.amount, note=body.note)
    db.add(payment)
    db.flush()
    _resync_status(db, loan)
    record_audit(
        db, "loan_payment_added", user_id=user.id, ip=client_ip(request), entity_type="loan", entity_id=str(loan.id),
        details={"payment_id": str(payment.id), "amount": str(body.amount), "status": loan.status},
    )
    db.commit()
    return _detail(db, user, loan)


@router.delete("/{loan_id}/payments/{payment_id}", response_model=LoanDetailOut)
def delete_payment(
    loan_id: uuid.UUID, payment_id: uuid.UUID, request: Request,
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    loan = _owned(db, user, loan_id, lock=True)
    payment = db.scalar(select(LoanPayment).where(LoanPayment.id == payment_id, LoanPayment.loan_id == loan.id))
    if payment is None:
        raise HTTPException(404, "Payment not found.")
    amount = payment.amount
    db.delete(payment)
    db.flush()
    _resync_status(db, loan)
    record_audit(
        db, "loan_payment_deleted", user_id=user.id, ip=client_ip(request), entity_type="loan", entity_id=str(loan.id),
        details={"payment_id": str(payment_id), "amount": str(amount), "status": loan.status},
    )
    db.commit()
    return _detail(db, user, loan)
