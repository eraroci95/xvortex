from datetime import date
from decimal import Decimal as D

import pytest

pytest.importorskip("pydantic")
from pydantic import ValidationError  # noqa: E402

from app.api.loan_schemas import BorrowerIn, BorrowerPatch, LoanIn, LoanPatch, PaymentIn  # noqa: E402

BASE = dict(
    borrower_id="00000000-0000-0000-0000-000000000001", principal="1000.00", annual_interest_rate="7.5",
    start_date="2026-01-01", maturity_date="2026-12-01",
)


def test_valid_loan_gets_defaults():
    loan = LoanIn(**BASE)
    assert loan.currency == "SEK" and loan.repayment_frequency == "monthly" and loan.amortization_method == "annuity"
    assert loan.principal == D("1000.00")


@pytest.mark.parametrize("change", [
    {"principal": "0"}, {"principal": "-5"}, {"principal": "10.123"}, {"principal": "12345678901234567.00"},
    {"annual_interest_rate": "-1"}, {"annual_interest_rate": "1000"}, {"annual_interest_rate": "1.00001"},
    {"currency": "sek"}, {"currency": "SE"}, {"currency": "SEKK"},
    {"repayment_frequency": "daily"}, {"amortization_method": "balloon"},
    {"maturity_date": "2026-01-01"}, {"maturity_date": "2025-01-01"},
])
def test_invalid_loans_are_rejected(change):
    with pytest.raises(ValidationError):
        LoanIn(**{**BASE, **change})


def test_borrower_trims_and_clears_blanks():
    b = BorrowerIn(name="  Anna  ", email="  ", phone="", notes="  ")
    assert b.name == "Anna" and b.email is None and b.phone is None and b.notes is None
    with pytest.raises(ValidationError):
        BorrowerIn(name="   ")
    with pytest.raises(ValidationError):
        BorrowerIn(name="A", email="not-an-email")


def test_borrower_patch_only_sets_what_is_sent():
    p = BorrowerPatch(email="")
    assert p.model_fields_set == {"email"} and p.email is None  # blank clears
    with pytest.raises(ValidationError):
        BorrowerPatch(email="bad")
    with pytest.raises(ValidationError):
        BorrowerPatch(name=" ")


def test_loan_patch_cannot_set_repaid_by_hand():
    assert LoanPatch(status="closed").status == "closed"
    with pytest.raises(ValidationError):
        LoanPatch(status="repaid")


def test_payment_rules():
    assert PaymentIn(paid_on=date(2026, 2, 1), amount="10.50", note=" x ").note == "x"
    for bad in ("0", "-1", "1.005"):
        with pytest.raises(ValidationError):
            PaymentIn(paid_on=date(2026, 2, 1), amount=bad)
