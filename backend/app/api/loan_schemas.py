"""Request and response shapes for borrowers, loans and payments. Imports only pydantic."""
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Frequency = Literal["weekly", "biweekly", "monthly", "quarterly", "semiannual", "annual"]
Method = Literal["annuity", "equal_principal", "interest_only"]
LoanStatus = Literal["active", "repaid", "closed"]
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _email_or_none(v: str | None) -> str | None:
    v = _clean(v)
    if v is not None and not re.match(EMAIL_PATTERN, v):
        raise ValueError("Enter a valid email address.")
    return v


class BorrowerIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank.")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return _email_or_none(v)

    @field_validator("phone", "notes")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return _clean(v)


class BorrowerPatch(BaseModel):
    """Only the fields sent are changed. Send an empty string to clear email, phone or notes."""
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=5000)
    archived: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank.")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        return _email_or_none(v)


class BorrowerOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    notes: str | None
    archived: bool
    loan_count: int
    active_loan_count: int
    created_at: datetime


class LoanTermsIn(BaseModel):
    principal: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    annual_interest_rate: Decimal = Field(ge=0, lt=1000, max_digits=7, decimal_places=4)
    currency: str = Field(default="SEK", pattern=r"^[A-Z]{3}$")
    start_date: date
    maturity_date: date
    repayment_frequency: Frequency = "monthly"
    amortization_method: Method = "annuity"

    @model_validator(mode="after")
    def _dates(self):
        if self.maturity_date <= self.start_date:
            raise ValueError("Maturity date must be after the start date.")
        return self


class LoanIn(LoanTermsIn):
    borrower_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("notes")
    @classmethod
    def _notes(cls, v: str | None) -> str | None:
        return _clean(v)


class LoanPatch(BaseModel):
    notes: str | None = Field(default=None, max_length=5000)
    status: Literal["active", "closed"] | None = None  # repaid is automatic, never set by hand
    archived: bool | None = None


class PaymentIn(BaseModel):
    paid_on: date
    amount: Decimal = Field(gt=0, max_digits=16, decimal_places=2)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note")
    @classmethod
    def _note(cls, v: str | None) -> str | None:
        return _clean(v)


class InstallmentOut(BaseModel):
    number: int
    due_date: date
    principal: Decimal
    interest: Decimal
    total: Decimal
    paid_principal: Decimal
    paid_interest: Decimal
    outstanding: Decimal
    status: Literal["paid", "partial", "overdue", "upcoming"]


class PaymentOut(BaseModel):
    id: uuid.UUID
    paid_on: date
    amount: Decimal
    note: str | None


class PreviewOut(BaseModel):
    installments: list[InstallmentOut]
    total_principal: Decimal
    total_interest: Decimal
    total_repayable: Decimal


class RiskOut(BaseModel):
    level: Literal["low", "medium", "high"]
    triggers: list[str]
    disclaimer: str


class LoanSummaryOut(BaseModel):
    id: uuid.UUID
    borrower_id: uuid.UUID
    borrower_name: str
    principal: Decimal
    annual_interest_rate: Decimal
    currency: str
    start_date: date
    maturity_date: date
    repayment_frequency: str
    amortization_method: str
    status: str
    archived: bool
    outstanding_principal: Decimal
    remaining_interest: Decimal
    overdue_amount: Decimal
    overdue_installments: int
    unapplied_payments: Decimal
    next_due_date: date | None
    next_due_amount: Decimal | None
    risk: RiskOut | None  # only for active, unarchived loans


class LoanDetailOut(LoanSummaryOut):
    notes: str | None
    created_at: datetime
    total_paid: Decimal
    schedule: list[InstallmentOut]
    payments: list[PaymentOut]
