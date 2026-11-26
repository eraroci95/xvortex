"""Portfolio-level loan totals, grouped by currency (amounts in different currencies are never added)."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .amortization import Installment, allocate_payments, money, outstanding_principal, remaining_interest
from .risk import overdue_installments

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class LoanSnapshot:
    loan_id: object
    currency: str
    principal: Decimal
    schedule: list[Installment]
    payments: list[Decimal]


@dataclass
class CurrencyTotals:
    currency: str
    active_loans: int = 0
    overdue_loans: int = 0
    total_lent: Decimal = ZERO
    outstanding_principal: Decimal = ZERO
    remaining_interest: Decimal = ZERO
    overdue_amount: Decimal = ZERO
    unapplied_payments: Decimal = ZERO  # paid beyond everything the schedule asks for
    loan_ids: list = field(default_factory=list)


def summarize_loans(loans: list[LoanSnapshot], today: date) -> list[CurrencyTotals]:
    """A loan with no stored schedule falls back to principal minus payments (never below zero).
    Payments beyond what a loan owes are reported as `unapplied_payments`, not silently dropped."""
    by_currency: dict[str, CurrencyTotals] = {}
    for loan in loans:
        t = by_currency.setdefault(loan.currency, CurrencyTotals(loan.currency))
        t.active_loans += 1
        t.total_lent += loan.principal
        t.loan_ids.append(loan.loan_id)
        if not loan.schedule:
            paid = sum(loan.payments, ZERO)
            t.outstanding_principal += max(loan.principal - paid, ZERO)
            t.unapplied_payments += max(paid - loan.principal, ZERO)
            continue
        allocations, excess = allocate_payments(loan.schedule, loan.payments)
        t.unapplied_payments += excess
        t.outstanding_principal += outstanding_principal(allocations)
        t.remaining_interest += remaining_interest(allocations)
        overdue = overdue_installments(allocations, today)
        if overdue:
            t.overdue_loans += 1
            t.overdue_amount += sum((a.principal_outstanding + a.interest_outstanding for a, _ in overdue), ZERO)
    for t in by_currency.values():
        for name in ("total_lent", "outstanding_principal", "remaining_interest", "overdue_amount", "unapplied_payments"):
            setattr(t, name, money(getattr(t, name)))
    return sorted(by_currency.values(), key=lambda t: t.currency)
