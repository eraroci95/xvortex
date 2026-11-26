"""Borrower, loan and payment endpoints (needs the full dependency set)."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("argon2")

from sqlalchemy import select  # noqa: E402

from app.models import AuditLog, Loan, LoanRepaymentSchedule  # noqa: E402
from tests.helpers import login_csrf  # noqa: E402

START = date.today() - timedelta(days=100)
MATURITY = START + timedelta(days=180)


def _borrower(client, h, name="Anna"):
    r = client.post("/api/borrowers", json={"name": name}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _loan(client, h, borrower_id, **over):
    body = {
        "borrower_id": borrower_id, "principal": "1200.00", "annual_interest_rate": "12", "currency": "SEK",
        "start_date": START.isoformat(), "maturity_date": MATURITY.isoformat(),
        "repayment_frequency": "monthly", "amortization_method": "equal_principal", **over,
    }
    return client.post("/api/loans", json=body, headers=h)


def _total(loan) -> D:
    return sum((D(i["total"]) for i in loan["schedule"]), D("0"))


def test_endpoints_need_sign_in_and_csrf(client):
    for path in ("/api/borrowers", "/api/loans", "/api/loans/00000000-0000-0000-0000-000000000000"):
        assert client.get(path).status_code == 401
    h = login_csrf(client)
    assert client.post("/api/borrowers", json={"name": "x"}).status_code == 403  # no CSRF header
    assert client.post("/api/borrowers", json={"name": "x"}, headers=h).status_code == 201


def test_borrower_create_update_archive(client):
    h = login_csrf(client)
    bid = _borrower(client, h)
    r = client.patch(f"/api/borrowers/{bid}", json={"email": "anna@example.com", "phone": "123"}, headers=h)
    assert r.json()["email"] == "anna@example.com" and r.json()["name"] == "Anna"
    assert client.patch(f"/api/borrowers/{bid}", json={"email": ""}, headers=h).json()["email"] is None
    assert client.patch(f"/api/borrowers/{bid}", json={"email": "bad"}, headers=h).status_code == 422
    assert client.patch(f"/api/borrowers/{bid}", json={"archived": True}, headers=h).json()["archived"] is True
    assert client.get("/api/borrowers").json() == []
    assert len(client.get("/api/borrowers?include_archived=true").json()) == 1
    assert client.patch(f"/api/borrowers/{bid}", json={"archived": False}, headers=h).json()["archived"] is False


def test_preview_does_not_save_anything(client):
    h = login_csrf(client)
    body = {
        "principal": "1200", "annual_interest_rate": "12", "start_date": START.isoformat(),
        "maturity_date": MATURITY.isoformat(), "repayment_frequency": "monthly", "amortization_method": "annuity",
    }
    r = client.post("/api/loans/preview", json=body, headers=h)
    assert r.status_code == 200
    out = r.json()
    assert D(out["total_principal"]) == D("1200.00")
    assert D(out["total_repayable"]) == D(out["total_principal"]) + D(out["total_interest"])
    assert len(out["installments"]) == 6
    assert client.get("/api/loans?view=all").json() == []
    body["repayment_frequency"] = "weekly"
    body["maturity_date"] = (START + timedelta(days=365 * 30)).isoformat()
    assert client.post("/api/loans/preview", json=body, headers=h).status_code == 422  # too many installments


def test_create_loan_stores_schedule_and_audits(client):
    h = login_csrf(client)
    r = _loan(client, h, _borrower(client, h))
    assert r.status_code == 201, r.text
    loan = r.json()
    assert loan["status"] == "active" and loan["borrower_name"] == "Anna" and len(loan["schedule"]) == 6
    assert D(loan["outstanding_principal"]) == D("1200.00") and loan["payments"] == []
    with client.Session() as s:
        assert len(s.scalars(select(LoanRepaymentSchedule)).all()) == 6
        assert "loan_created" in s.scalars(select(AuditLog.action)).all()


def test_create_loan_validation(client):
    h = login_csrf(client)
    bid = _borrower(client, h)
    assert _loan(client, h, bid, principal="0").status_code == 422
    assert _loan(client, h, bid, currency="sek").status_code == 422
    assert _loan(client, h, bid, maturity_date=START.isoformat()).status_code == 422
    assert _loan(client, h, "00000000-0000-0000-0000-000000000009").status_code == 404
    client.patch(f"/api/borrowers/{bid}", json={"archived": True}, headers=h)
    assert _loan(client, h, bid).status_code == 409


def test_payments_drive_status_both_ways(client):
    h = login_csrf(client)
    loan = _loan(client, h, _borrower(client, h)).json()
    lid, total = loan["id"], _total(loan)

    r = client.post(f"/api/loans/{lid}/payments", json={"paid_on": START.isoformat(), "amount": "212.00"}, headers=h)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "active" and D(d["outstanding_principal"]) == D("1000.00")
    assert d["schedule"][0]["status"] == "paid" and D(d["total_paid"]) == D("212.00")

    rest = total - D("212.00")
    d = client.post(
        f"/api/loans/{lid}/payments", json={"paid_on": date.today().isoformat(), "amount": str(rest)}, headers=h,
    ).json()
    assert d["status"] == "repaid" and D(d["outstanding_principal"]) == D("0.00") and d["next_due_date"] is None
    assert d["risk"] is None  # only open loans carry a risk rating

    # a repaid loan takes no more payments
    again = client.post(f"/api/loans/{lid}/payments", json={"paid_on": date.today().isoformat(), "amount": "1"}, headers=h)
    assert again.status_code == 409

    # deleting a payment reopens it
    pid = d["payments"][-1]["id"]
    d = client.delete(f"/api/loans/{lid}/payments/{pid}", headers=h).json()
    assert d["status"] == "active" and D(d["outstanding_principal"]) > 0
    assert client.delete(f"/api/loans/{lid}/payments/{pid}", headers=h).status_code == 404


def test_payment_date_rules_and_overpayment(client):
    h = login_csrf(client)
    loan = _loan(client, h, _borrower(client, h)).json()
    lid = loan["id"]
    pay = lambda on, amt: client.post(f"/api/loans/{lid}/payments", json={"paid_on": on, "amount": amt}, headers=h)  # noqa: E731
    assert pay((START - timedelta(days=1)).isoformat(), "10").status_code == 422
    assert pay((date.today() + timedelta(days=1)).isoformat(), "10").status_code == 422
    assert pay(date.today().isoformat(), "0").status_code == 422
    d = pay(date.today().isoformat(), str(_total(loan) + D("50"))).json()
    assert d["status"] == "repaid" and D(d["unapplied_payments"]) == D("50.00")


def test_closing_archiving_and_reopening(client):
    h = login_csrf(client)
    loan = _loan(client, h, _borrower(client, h)).json()
    lid = loan["id"]
    assert client.patch(f"/api/loans/{lid}", json={"archived": True}, headers=h).status_code == 409  # still active
    d = client.patch(f"/api/loans/{lid}", json={"status": "closed", "notes": "written off"}, headers=h).json()
    assert d["status"] == "closed" and d["notes"] == "written off" and d["risk"] is None
    assert client.post(f"/api/loans/{lid}/payments", json={"paid_on": date.today().isoformat(), "amount": "5"}, headers=h).status_code == 409
    assert client.patch(f"/api/loans/{lid}", json={"archived": True}, headers=h).json()["archived"] is True
    assert client.get("/api/loans?view=active").json() == []
    assert client.get("/api/loans?view=finished").json() == []
    assert len(client.get("/api/loans?view=archived").json()) == 1
    client.patch(f"/api/loans/{lid}", json={"archived": False}, headers=h)
    assert len(client.get("/api/loans?view=finished").json()) == 1
    d = client.patch(f"/api/loans/{lid}", json={"status": "active"}, headers=h).json()
    assert d["status"] == "active"
    assert client.patch(f"/api/loans/{lid}", json={"status": "repaid"}, headers=h).status_code == 422


def test_overdue_loan_is_listed_with_figures_and_risk(client):
    h = login_csrf(client)
    _loan(client, h, _borrower(client, h))
    row = client.get("/api/loans").json()[0]
    assert row["overdue_installments"] >= 3 and D(row["overdue_amount"]) > 0
    assert row["risk"]["level"] == "high" and row["risk"]["triggers"]
    assert row["next_due_date"] < date.today().isoformat()  # the oldest unpaid installment, already late


def test_borrower_with_active_loan_cannot_be_archived(client):
    h = login_csrf(client)
    bid = _borrower(client, h)
    lid = _loan(client, h, bid).json()["id"]
    assert client.patch(f"/api/borrowers/{bid}", json={"archived": True}, headers=h).status_code == 409
    row = client.get("/api/borrowers").json()[0]
    assert row["loan_count"] == 1 and row["active_loan_count"] == 1
    client.patch(f"/api/loans/{lid}", json={"status": "closed"}, headers=h)
    assert client.patch(f"/api/borrowers/{bid}", json={"archived": True}, headers=h).status_code == 200


def test_users_cannot_see_or_change_each_others_loans(client):
    admin = login_csrf(client)
    bid = _borrower(client, admin)
    lid = _loan(client, admin, bid).json()["id"]

    other = login_csrf(client, "user@example.com")
    assert client.get("/api/loans?view=all").json() == [] and client.get("/api/borrowers").json() == []
    assert client.get(f"/api/loans/{lid}").status_code == 404
    assert client.patch(f"/api/loans/{lid}", json={"status": "closed"}, headers=other).status_code == 404
    assert client.post(f"/api/loans/{lid}/payments", json={"paid_on": date.today().isoformat(), "amount": "5"}, headers=other).status_code == 404
    assert client.patch(f"/api/borrowers/{bid}", json={"name": "Mine now"}, headers=other).status_code == 404
    assert _loan(client, other, bid).status_code == 404  # someone else's borrower

    with client.Session() as s:
        assert s.scalar(select(Loan.status).where(Loan.id == lid)) == "active"
