"""Transparent, rule-based loan risk indicators.

These are descriptive flags derived from payment history, not a prediction of default.
Every flag lists the rule that triggered it so the user can see exactly why.

An installment that is only a few days late is not flagged (the overdue_days_medium grace period);
the dashboard still counts it as overdue. Portfolio figures passed in must be in the same currency
as the loan being assessed: amounts in different currencies are never added together.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .amortization import Allocation

DISCLAIMER = (
    "Risk indicators are rule-based summaries of past payment behaviour. "
    "They are not a prediction and not a guarantee of repayment or default."
)


@dataclass(frozen=True)
class RiskRules:
    overdue_days_medium: int = 7  # grace period: a shorter delay is not flagged
    overdue_days_high: int = 30
    missed_medium: int = 2
    missed_high: int = 3
    exposure_share_high: Decimal = Decimal("0.40")  # share of total portfolio outstanding
    exposure_min_loans: int = 3  # with fewer loans, any one of them is a large share by construction


@dataclass
class RiskAssessment:
    level: str  # "low" | "medium" | "high"
    triggers: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER


def overdue_installments(allocations: list[Allocation], today: date) -> list[tuple[Allocation, int]]:
    return [
        (a, (today - a.installment.due_date).days)
        for a in allocations
        if a.installment.due_date < today and not a.is_settled
    ]


def assess_loan(
    allocations: list[Allocation],
    today: date,
    outstanding: Decimal,
    portfolio_outstanding: Decimal,
    portfolio_loans: int,
    rules: RiskRules = RiskRules(),
) -> RiskAssessment:
    overdue = overdue_installments(allocations, today)
    missed = len(overdue)
    max_days = max((d for _, d in overdue), default=0)
    level, triggers = "low", []

    def raise_to(new: str, why: str) -> None:
        nonlocal level
        order = {"low": 0, "medium": 1, "high": 2}
        triggers.append(why)
        if order[new] > order[level]:
            level = new

    if max_days >= rules.overdue_days_high:
        raise_to("high", f"An installment is {max_days} days overdue (high threshold {rules.overdue_days_high}).")
    elif max_days >= rules.overdue_days_medium:
        raise_to("medium", f"An installment is {max_days} days overdue (medium threshold {rules.overdue_days_medium}).")
    if missed >= rules.missed_high:
        raise_to("high", f"{missed} installments are unpaid past due (high threshold {rules.missed_high}).")
    elif missed >= rules.missed_medium:
        raise_to("medium", f"{missed} installments are unpaid past due (medium threshold {rules.missed_medium}).")
    if (
        portfolio_loans >= rules.exposure_min_loans
        and portfolio_outstanding > 0
        and outstanding / portfolio_outstanding >= rules.exposure_share_high
    ):
        share = (outstanding / portfolio_outstanding * 100).quantize(Decimal("0.1"))
        raise_to("medium", f"This loan is {share}% of total outstanding principal.")
    return RiskAssessment(level, triggers)
