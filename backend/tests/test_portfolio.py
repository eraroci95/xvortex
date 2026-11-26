from datetime import date
from decimal import Decimal as D

from app.services.loans.amortization import build_schedule
from app.services.loans.portfolio import LoanSnapshot, summarize_loans

TODAY = date(2026, 3, 15)


def _loan(currency="SEK", principal="1200", paid=(), start=date(2026, 1, 1), maturity=date(2026, 7, 1)):
    s = build_schedule(D(principal), D("12"), start, maturity, "monthly", "equal_principal")
    return LoanSnapshot(object(), currency, D(principal), s, [D(p) for p in paid])


def test_empty_portfolio():
    assert summarize_loans([], TODAY) == []


def test_totals_and_overdue_for_unpaid_loan():
    (t,) = summarize_loans([_loan()], TODAY)
    assert t.active_loans == 1 and t.overdue_loans == 1  # Feb 1 and Mar 1 installments unpaid
    assert t.total_lent == D("1200.00") and t.outstanding_principal == D("1200.00")
    assert t.overdue_amount == D("422.00")  # 200 + 12 interest, then 200 + 10 interest


def test_payments_reduce_balances_and_currencies_stay_separate():
    paid = _loan(paid=["100"], start=date(2026, 3, 1), maturity=date(2026, 9, 1))
    usd = _loan(currency="USD", principal="500", start=date(2026, 3, 1), maturity=date(2026, 9, 1))
    sek_t, usd_t = summarize_loans([paid, usd], TODAY)
    assert (sek_t.currency, usd_t.currency) == ("SEK", "USD")
    assert sek_t.outstanding_principal == D("1112.00") and sek_t.overdue_loans == 0
    assert usd_t.total_lent == D("500.00")


def test_loan_without_schedule_falls_back_to_principal_minus_payments():
    snap = LoanSnapshot(object(), "SEK", D("1000"), [], [D("300"), D("900")])
    (t,) = summarize_loans([snap], TODAY)
    assert t.outstanding_principal == D("0.00") and t.overdue_loans == 0


def test_overpayment_is_reported_not_dropped():
    over = _loan(paid=["99999"])  # far more than the schedule asks for
    no_schedule = LoanSnapshot(object(), "SEK", D("1000"), [], [D("1300")])
    (t,) = summarize_loans([over, no_schedule], TODAY)
    exact_total = sum(i.total for i in over.schedule)
    assert t.outstanding_principal == D("0.00") and t.overdue_loans == 0
    assert t.unapplied_payments == (D("99999") - exact_total + D("300")).quantize(D("0.01"))
    (clean,) = summarize_loans([_loan()], TODAY)
    assert clean.unapplied_payments == D("0.00")
