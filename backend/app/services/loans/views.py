"""Per-loan figures for the Loans screens, computed from the stored schedule and payments.

Pure functions over plain data (no database), so every rule here is covered by fast unit tests.
Nothing is estimated: a loan's numbers come only from its own schedule and recorded payments.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .amortization import (
    Allocation, Installment, allocate_payments, money, outstanding_principal, remaining_interest,
)
from .risk import RiskAssessment, RiskRules, assess_loan, overdue_installments

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class LoanFacts:
    loan_id: object
    currency: str
    principal: Decimal
    status: str  # active | repaid | closed
    archived: bool
    schedule: list[Installment]
    payments: list[Decimal]


@dataclass(frozen=True)
class LoanFigures:
    allocations: list[Allocation]
    unapplied: Decimal  # paid beyond everything the schedule asks for
    outstanding_principal: Decimal
    remaining_interest: Decimal
    overdue: list[tuple[Allocation, int]]  # (installment, days overdue)
    overdue_amount: Decimal
    settled: bool  # every installment fully paid
    next_due: Allocation | None  # earliest installment not fully paid (may already be overdue)


def compute_figures(facts: LoanFacts, today: date) -> LoanFigures:
    """A loan without a stored schedule falls back to principal minus payments."""
    if facts.schedule:
        allocations, unapplied = allocate_payments(facts.schedule, facts.payments)
        overdue = overdue_installments(allocations, today)
        return LoanFigures(
            allocations=allocations,
            unapplied=money(unapplied),
            outstanding_principal=money(outstanding_principal(allocations)),
            remaining_interest=money(remaining_interest(allocations)),
            overdue=overdue,
            overdue_amount=money(sum((a.principal_outstanding + a.interest_outstanding for a, _ in overdue), ZERO)),
            settled=all(a.is_settled for a in allocations),
            next_due=next((a for a in allocations if not a.is_settled), None),
        )
    paid = sum(facts.payments, ZERO)
    return LoanFigures(
        allocations=[], unapplied=money(max(paid - facts.principal, ZERO)),
        outstanding_principal=money(max(facts.principal - paid, ZERO)), remaining_interest=ZERO,
        overdue=[], overdue_amount=ZERO, settled=paid >= facts.principal, next_due=None,
    )


def installment_status(a: Allocation, today: date) -> str:
    if a.is_settled:
        return "paid"
    if a.installment.due_date < today:
        return "overdue"
    if a.paid_principal > 0 or a.paid_interest > 0:
        return "partial"
    return "upcoming"


def desired_status(current: str, figures: LoanFigures) -> str:
    """The status after payments change. active and repaid follow the figures automatically; a loan
    closed by hand stays closed until the user reopens it."""
    if current == "closed":
        return current
    return "repaid" if figures.settled else "active"


def assess_all(
    loans: list[tuple[LoanFacts, LoanFigures]], today: date, rules: RiskRules = RiskRules(),
) -> dict[object, RiskAssessment]:
    """Risk for each active, unarchived loan. Concentration compares a loan with the other open loans
    in its own currency; amounts in different currencies are never added together."""
    open_loans = [(f, fig) for f, fig in loans if f.status == "active" and not f.archived]
    outstanding: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    for f, fig in open_loans:
        outstanding[f.currency] = outstanding.get(f.currency, ZERO) + fig.outstanding_principal
        counts[f.currency] = counts.get(f.currency, 0) + 1
    return {
        f.loan_id: assess_loan(
            fig.allocations, today, fig.outstanding_principal, outstanding[f.currency], counts[f.currency], rules,
        )
        for f, fig in open_loans
    }


def schedule_totals(schedule: list[Installment]) -> tuple[Decimal, Decimal, Decimal]:
    """(total principal, total interest, total repayable) over the whole schedule."""
    principal = sum((i.principal for i in schedule), ZERO)
    interest = sum((i.interest for i in schedule), ZERO)
    return money(principal), money(interest), money(principal + interest)
