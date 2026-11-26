from datetime import date
from decimal import Decimal as D

from app.services.loans.amortization import allocate_payments, build_schedule
from app.services.loans.risk import assess_loan


def _allocs(paid):
    s = build_schedule(D("1200"), D("12"), date(2026, 1, 1), date(2026, 7, 1), "monthly", "equal_principal")
    a, _ = allocate_payments(s, [D(paid)])
    return a


def test_on_time_is_low():
    r = assess_loan(_allocs("0"), date(2026, 1, 1), D("1200"), D("5000"), 4)
    assert r.level == "low" and r.triggers == []


def test_overdue_thresholds():
    # First installment is due Feb 1: grace period, then medium at 7 days, high at 30.
    assert assess_loan(_allocs("0"), date(2026, 2, 2), D("1200"), D("5000"), 4).level == "low"
    assert assess_loan(_allocs("0"), date(2026, 2, 7), D("1200"), D("5000"), 4).level == "low"
    assert assess_loan(_allocs("0"), date(2026, 2, 8), D("1200"), D("5000"), 4).level == "medium"
    assert assess_loan(_allocs("0"), date(2026, 3, 3), D("1200"), D("5000"), 4).level == "high"


def test_two_installments_past_due_is_medium_even_when_each_is_only_days_late():
    # Feb 1 and Mar 1 both unpaid on Mar 3: 30 and 2 days late.
    r = assess_loan(_allocs("0"), date(2026, 3, 3), D("1200"), D("5000"), 4)
    assert any("2 installments" in t for t in r.triggers)
    r = assess_loan(_allocs("0"), date(2026, 4, 15), D("1200"), D("5000"), 4)
    assert r.level == "high" and any("3 installments" in t for t in r.triggers)


def test_concentration_flag_and_disclaimer():
    r = assess_loan(_allocs("0"), date(2026, 1, 1), D("1200"), D("1500"), 3)
    assert r.level == "medium" and "total outstanding" in r.triggers[0]
    assert "not a prediction" in r.disclaimer


def test_concentration_is_ignored_for_very_small_portfolios():
    for loans, total in ((1, "1200"), (2, "2400")):
        r = assess_loan(_allocs("0"), date(2026, 1, 1), D("1200"), D(total), loans)
        assert r.level == "low" and r.triggers == [], loans
