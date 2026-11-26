from datetime import date
from decimal import Decimal as D

from app.services.loans.amortization import allocate_payments, build_schedule
from app.services.loans.views import (
    LoanFacts, assess_all, compute_figures, desired_status, installment_status, schedule_totals,
)

TODAY = date(2026, 3, 15)


def _facts(loan_id="a", currency="SEK", principal="1200", paid=(), status="active", archived=False,
           start=date(2026, 1, 1), maturity=date(2026, 7, 1)):
    schedule = build_schedule(D(principal), D("12"), start, maturity, "monthly", "equal_principal")
    return LoanFacts(loan_id, currency, D(principal), status, archived, schedule, [D(p) for p in paid])


def test_figures_for_an_unpaid_loan_with_two_overdue_installments():
    fig = compute_figures(_facts(), TODAY)  # Feb 1 and Mar 1 are past due
    assert fig.outstanding_principal == D("1200.00") and fig.settled is False
    assert len(fig.overdue) == 2 and fig.overdue_amount == D("422.00")
    assert fig.next_due.installment.number == 1 and fig.unapplied == D("0.00")


def test_payments_move_the_next_due_installment_and_reduce_balances():
    fig = compute_figures(_facts(paid=["212", "100"]), TODAY)  # installment 1 in full, 100 into installment 2
    assert fig.outstanding_principal == D("910.00")  # 1200 less 200 (installment 1) less 90 (part of 2)
    assert fig.next_due.installment.number == 2
    assert fig.next_due.paid_interest == D("10.00") and fig.next_due.paid_principal == D("90.00")
    assert len(fig.overdue) == 1  # installment 2 is still partly unpaid and past due


def test_loan_is_settled_when_every_installment_is_paid_and_extra_is_reported():
    s = _facts()
    total = sum(i.total for i in s.schedule)
    fig = compute_figures(_facts(paid=[str(total + D("5"))]), TODAY)
    assert fig.settled and fig.next_due is None and fig.outstanding_principal == D("0.00")
    assert fig.unapplied == D("5.00")


def test_loan_without_schedule_uses_principal_minus_payments():
    facts = LoanFacts("x", "SEK", D("1000"), "active", False, [], [D("300")])
    fig = compute_figures(facts, TODAY)
    assert fig.outstanding_principal == D("700.00") and not fig.settled
    done = compute_figures(LoanFacts("x", "SEK", D("1000"), "active", False, [], [D("1100")]), TODAY)
    assert done.settled and done.unapplied == D("100.00")


def test_installment_status_labels():
    s = _facts().schedule
    allocs, _ = allocate_payments(s, [D("212"), D("50")])
    labels = [installment_status(a, TODAY) for a in allocs]
    assert labels[0] == "paid"
    assert labels[1] == "overdue"  # partly paid but past due
    assert labels[2] == "upcoming" and labels[-1] == "upcoming"
    early, _ = allocate_payments(s, [D("50")])
    assert installment_status(early[0], date(2026, 1, 15)) == "partial"


def test_desired_status_follows_payments_but_never_reopens_a_closed_loan():
    paid_up = compute_figures(_facts(paid=[str(sum(i.total for i in _facts().schedule))]), TODAY)
    unpaid = compute_figures(_facts(), TODAY)
    assert desired_status("active", paid_up) == "repaid"
    assert desired_status("repaid", unpaid) == "active"
    assert desired_status("closed", paid_up) == "closed" and desired_status("closed", unpaid) == "closed"


def test_risk_is_only_for_open_loans_and_concentration_stays_within_a_currency():
    loans = []
    for i in range(3):
        f = _facts(loan_id=f"sek{i}", start=date(2026, 3, 1), maturity=date(2026, 9, 1))
        loans.append((f, compute_figures(f, TODAY)))
    usd = _facts(loan_id="usd", currency="USD", principal="50000", start=date(2026, 3, 1), maturity=date(2026, 9, 1))
    closed = _facts(loan_id="closed", status="closed")
    archived = _facts(loan_id="arch", archived=True)
    loans += [(f, compute_figures(f, TODAY)) for f in (usd, closed, archived)]
    risk = assess_all(loans, TODAY)
    assert set(risk) == {"sek0", "sek1", "sek2", "usd"}  # no entries for closed or archived loans
    assert risk["usd"].level == "low"  # alone in its currency: a share of one loan means nothing
    assert all(risk[f"sek{i}"].level == "low" for i in range(3))  # 33% each, below the 40% flag


def test_risk_flags_a_dominant_loan_among_three_and_overdue_loans():
    big = _facts(loan_id="big", principal="9000", start=date(2026, 3, 1), maturity=date(2026, 9, 1))
    small = [_facts(loan_id=f"s{i}", principal="500", start=date(2026, 3, 1), maturity=date(2026, 9, 1)) for i in range(2)]
    late = _facts(loan_id="late", principal="500")  # Feb 1 and Mar 1 unpaid
    risk = assess_all([(f, compute_figures(f, TODAY)) for f in (big, *small, late)], TODAY)
    assert risk["big"].level == "medium" and "total outstanding" in risk["big"].triggers[0]
    assert risk["late"].level == "high"  # Feb 1 installment is 42 days overdue
    assert risk["s0"].level == "low"


def test_schedule_totals():
    p, i, total = schedule_totals(_facts().schedule)
    assert p == D("1200.00") and total == p + i and i > 0
