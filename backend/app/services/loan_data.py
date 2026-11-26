"""Loads the stored schedule and payments for loans and shapes them for the API."""
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.loan_schemas import InstallmentOut, LoanSummaryOut, RiskOut
from app.models import Loan, LoanPayment, LoanRepaymentSchedule
from app.services.loans.amortization import Allocation, Installment, money
from app.services.loans.risk import RiskAssessment
from app.services.loans.views import LoanFacts, LoanFigures, compute_figures, installment_status

ZERO = Decimal("0.00")


def load_facts(db: Session, loans: list[Loan]) -> list[LoanFacts]:
    if not loans:
        return []
    ids = [loan.id for loan in loans]
    schedule: dict = defaultdict(list)
    for r in db.scalars(
        select(LoanRepaymentSchedule).where(LoanRepaymentSchedule.loan_id.in_(ids))
        .order_by(LoanRepaymentSchedule.loan_id, LoanRepaymentSchedule.installment_no)
    ):
        schedule[r.loan_id].append(Installment(r.installment_no, r.due_date, r.principal_due, r.interest_due))
    payments: dict = defaultdict(list)
    for p in db.scalars(select(LoanPayment).where(LoanPayment.loan_id.in_(ids))):
        payments[p.loan_id].append(p.amount)
    return [
        LoanFacts(l.id, l.currency, l.principal, l.status, l.archived_at is not None, schedule[l.id], payments[l.id])
        for l in loans
    ]


def figures_for(facts: list[LoanFacts], today: date) -> list[tuple[LoanFacts, LoanFigures]]:
    return [(f, compute_figures(f, today)) for f in facts]


def installment_out(a: Allocation, today: date) -> InstallmentOut:
    i = a.installment
    return InstallmentOut(
        number=i.number, due_date=i.due_date, principal=i.principal, interest=i.interest, total=money(i.total),
        paid_principal=a.paid_principal, paid_interest=a.paid_interest,
        outstanding=money(a.principal_outstanding + a.interest_outstanding),
        status=installment_status(a, today),
    )


def risk_out(r: RiskAssessment | None) -> RiskOut | None:
    return None if r is None else RiskOut(level=r.level, triggers=r.triggers, disclaimer=r.disclaimer)


def summary_fields(loan: Loan, borrower_name: str, fig: LoanFigures, risk: RiskAssessment | None) -> dict:
    nxt = fig.next_due
    return dict(
        id=loan.id, borrower_id=loan.borrower_id, borrower_name=borrower_name, principal=loan.principal,
        annual_interest_rate=loan.annual_interest_rate, currency=loan.currency, start_date=loan.start_date,
        maturity_date=loan.maturity_date, repayment_frequency=loan.repayment_frequency,
        amortization_method=loan.amortization_method, status=loan.status, archived=loan.archived_at is not None,
        outstanding_principal=fig.outstanding_principal, remaining_interest=fig.remaining_interest,
        overdue_amount=fig.overdue_amount, overdue_installments=len(fig.overdue), unapplied_payments=fig.unapplied,
        next_due_date=nxt.installment.due_date if nxt else None,
        next_due_amount=money(nxt.principal_outstanding + nxt.interest_outstanding) if nxt else None,
        risk=risk_out(risk),
    )


def summary_out(loan: Loan, borrower_name: str, fig: LoanFigures, risk: RiskAssessment | None) -> LoanSummaryOut:
    return LoanSummaryOut(**summary_fields(loan, borrower_name, fig, risk))
