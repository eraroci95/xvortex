"""Dashboard summary, layout and notification endpoints (needs the full dependency set)."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("argon2")

from sqlalchemy import select  # noqa: E402

from app.models import (  # noqa: E402
    Borrower, Loan, LoanPayment, LoanRepaymentSchedule, Notification, PaperAccount, User,
)
from app.services.loans.amortization import build_schedule  # noqa: E402
from tests.helpers import login, login_csrf  # noqa: E402


def _admin_id(client):
    with client.Session() as s:
        return s.scalar(select(User.id).where(User.email == "admin@example.com"))


def test_empty_summary_has_zeroes_and_unavailable_markers(client):
    login(client)
    body = client.get("/api/dashboard/summary").json()
    assert body["loans"] == [] and body["transactions"] == []
    assert body["paper"]["accounts"] == 0
    assert body["paper"]["market_value"] is None and body["paper"]["valuation_status"] == "unavailable"
    assert body["market_data_status"] == "unavailable" and body["news"]["status"] == "unavailable"


def test_summary_uses_real_loan_rows(client):
    uid = _admin_id(client)
    start = date.today() + timedelta(days=1)
    with client.Session() as s:
        b = Borrower(user_id=uid, name="Test Borrower")
        s.add(b)
        s.flush()
        loan = Loan(
            user_id=uid, borrower_id=b.id, principal=D("1200.00"), annual_interest_rate=D("12"),
            currency="SEK", start_date=start, maturity_date=start + timedelta(days=180),
            repayment_frequency="monthly", amortization_method="equal_principal",
        )
        s.add(loan)
        s.flush()
        for i in build_schedule(D("1200"), D("12"), start, start + timedelta(days=180), "monthly", "equal_principal"):
            s.add(LoanRepaymentSchedule(
                loan_id=loan.id, installment_no=i.number, due_date=i.due_date,
                principal_due=i.principal, interest_due=i.interest,
            ))
        s.add(LoanPayment(loan_id=loan.id, paid_on=start, amount=D("100.00")))
        s.add(PaperAccount(user_id=uid, name="Main", starting_cash=D("1000"), cash_balance=D("1000")))
        s.commit()
    login(client)
    body = client.get("/api/dashboard/summary").json()
    sek = body["loans"][0]
    assert sek["currency"] == "SEK" and sek["active_loans"] == 1 and sek["overdue_loans"] == 0
    assert sek["total_lent"] == "1200.00" and sek["outstanding_principal"] == "1112.00"
    assert body["paper"]["cash"] == "1000.00"
    assert body["transactions"][0]["label"] == "Payment from Test Borrower"


def test_layout_defaults_roundtrip_and_validation(client):
    headers = login_csrf(client)
    default = client.get("/api/settings/dashboard-layout").json()["widgets"]
    assert [w["id"] for w in default][0] == "loans" and all(w["visible"] for w in default)
    reordered = list(reversed(default))
    reordered[0] = {**reordered[0], "visible": False}
    r = client.put("/api/settings/dashboard-layout", json={"widgets": reordered}, headers=headers)
    assert r.status_code == 200
    assert client.get("/api/settings/dashboard-layout").json()["widgets"] == reordered
    bad = [*default[:-1], {"id": "nope", "visible": True}]
    assert client.put("/api/settings/dashboard-layout", json={"widgets": bad}, headers=headers).status_code == 422
    dup = [*default[:-1], default[0]]
    assert client.put("/api/settings/dashboard-layout", json={"widgets": dup}, headers=headers).status_code == 422
    assert client.put("/api/settings/dashboard-layout", json={"widgets": default}).status_code == 403  # no CSRF


def test_notifications_are_private_and_markable(client):
    admin = _admin_id(client)
    with client.Session() as s:
        other = s.scalar(select(User.id).where(User.email == "user@example.com"))
        mine = Notification(user_id=admin, kind="loan", title="Mine")
        theirs = Notification(user_id=other, kind="loan", title="Theirs")
        s.add_all([mine, theirs])
        s.commit()
        mine_id, theirs_id = str(mine.id), str(theirs.id)
    headers = login_csrf(client)
    body = client.get("/api/notifications").json()
    assert body["unread"] == 1 and [n["title"] for n in body["items"]] == ["Mine"]
    assert client.post(f"/api/notifications/{theirs_id}/read", headers=headers).status_code == 404
    assert client.post(f"/api/notifications/{mine_id}/read", headers=headers).status_code == 204
    assert client.get("/api/notifications").json()["unread"] == 0
