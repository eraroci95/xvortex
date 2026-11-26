from datetime import date
from decimal import Decimal as D

import pytest

from app.services.loans.amortization import (
    MAX_INSTALLMENTS, allocate_payments, add_months, build_schedule, due_dates, final_period_fraction,
    outstanding_principal, remaining_interest,
)


def test_annuity_known_payment():
    s = build_schedule(D("10000"), D("12"), date(2026, 1, 15), date(2027, 1, 15), "monthly", "annuity")
    assert len(s) == 12
    assert s[0].total == D("888.49")  # standard 12-month, 12% nominal loan
    assert sum(i.principal for i in s) == D("10000.00")


def test_all_methods_principal_sums_to_exact_principal():
    for method in ("annuity", "equal_principal", "interest_only"):
        for freq in ("weekly", "biweekly", "monthly", "quarterly", "semiannual", "annual"):
            s = build_schedule(D("12345.67"), D("7.35"), date(2026, 1, 31), date(2028, 3, 15), freq, method)
            assert sum(i.principal for i in s) == D("12345.67"), (method, freq)
            assert s[-1].due_date == date(2028, 3, 15)


def test_zero_interest():
    s = build_schedule(D("1200"), D("0"), date(2026, 1, 1), date(2027, 1, 1), "monthly", "annuity")
    assert all(i.interest == 0 for i in s)
    assert sum(i.principal for i in s) == D("1200.00")


def test_equal_principal_and_interest_only_shapes():
    ep = build_schedule(D("1200"), D("12"), date(2026, 1, 1), date(2026, 7, 1), "monthly", "equal_principal")
    assert [i.principal for i in ep] == [D("200.00")] * 6
    assert ep[0].interest == D("12.00") and ep[1].interest == D("10.00")
    io = build_schedule(D("1000"), D("12"), date(2026, 1, 1), date(2026, 4, 1), "monthly", "interest_only")
    assert [i.principal for i in io] == [D("0.00"), D("0.00"), D("1000")]
    assert all(i.interest == D("10.00") for i in io)


def test_month_end_dates_clamp():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert due_dates(date(2026, 1, 31), date(2026, 4, 30), "monthly")[-1] == date(2026, 4, 30)


def test_invalid_inputs_raise():
    for args in [
        (D("0"), D("5"), date(2026, 1, 1), date(2027, 1, 1)),
        (D("100"), D("-1"), date(2026, 1, 1), date(2027, 1, 1)),
        (D("100"), D("5"), date(2027, 1, 1), date(2026, 1, 1)),
    ]:
        try:
            build_schedule(*args)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_allocation_partial_and_overpayment():
    s = build_schedule(D("1200"), D("12"), date(2026, 1, 1), date(2026, 7, 1), "monthly", "equal_principal")
    allocs, excess = allocate_payments(s, [D("100.00")])
    assert allocs[0].paid_interest == D("12.00") and allocs[0].paid_principal == D("88.00")
    assert excess == 0
    assert outstanding_principal(allocs) == D("1112.00")
    total_interest = sum(i.interest for i in s)
    assert remaining_interest(allocs) == total_interest - D("12.00")
    allocs, excess = allocate_payments(s, [D("999999")])
    assert outstanding_principal(allocs) == 0 and excess > 0


def test_short_final_period_charges_prorated_interest_not_a_full_period():
    # Regular dates run to May 31; maturity is Jun 1, one day into a 30-day period (May 31 to Jun 30).
    s = build_schedule(D("10000"), D("12"), date(2026, 1, 31), date(2026, 6, 1), "monthly", "annuity")
    assert [i.due_date for i in s][-2:] == [date(2026, 5, 31), date(2026, 6, 1)]
    assert s[-2].interest == D("40.60") and s[-1].interest == D("0.68")  # 2040.00 * 1% / 30 days
    assert sum(i.principal for i in s) == D("10000.00")


def test_schedule_ending_on_a_regular_date_is_unchanged():
    dates = due_dates(date(2026, 1, 1), date(2026, 7, 1), "monthly")
    assert final_period_fraction(date(2026, 1, 1), "monthly", dates) == 1
    s = build_schedule(D("1200"), D("12"), date(2026, 1, 1), date(2026, 7, 1), "monthly", "equal_principal")
    assert s[-1].interest == D("2.00")  # a full month on the last 200.00


def test_loan_shorter_than_one_period_is_prorated_too():
    s = build_schedule(D("1000"), D("12"), date(2026, 1, 1), date(2026, 1, 11), "monthly", "interest_only")
    assert len(s) == 1 and s[0].principal == D("1000.00")
    assert s[0].interest == D("3.23")  # 1000 * 1% * 10/31


def test_installment_count_is_capped():
    assert len(due_dates(date(2026, 1, 1), date(2126, 1, 1), "monthly")) == MAX_INSTALLMENTS
    for end in (date(2126, 2, 1), date(9999, 1, 1)):
        with pytest.raises(ValueError, match="more than"):
            due_dates(date(2026, 1, 1), end, "monthly")
    with pytest.raises(ValueError, match="more than"):
        build_schedule(D("1000"), D("5"), date(2026, 1, 1), date(2100, 1, 1), "weekly", "annuity")
