import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint, Uuid, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, Money, Rate, UUIDPk


class Borrower(Base):
    __tablename__ = "borrowers"
    __table_args__ = (Index("ix_borrowers_user_id_name", "user_id", "name"),)

    id: Mapped[UUIDPk]
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("principal > 0", name="principal_positive"),
        CheckConstraint("annual_interest_rate >= 0", name="rate_non_negative"),
        CheckConstraint("maturity_date > start_date", name="maturity_after_start"),
        Index("ix_loans_user_id_status", "user_id", "status"),
        Index("ix_loans_borrower_id", "borrower_id"),
    )

    id: Mapped[UUIDPk]
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    borrower_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("borrowers.id", ondelete="RESTRICT"))
    principal: Mapped[Money]
    annual_interest_rate: Mapped[Rate]  # percent, e.g. 7.5 means 7.5% per year
    currency: Mapped[str] = mapped_column(String(3), server_default="SEK")
    start_date: Mapped[date] = mapped_column(Date)
    maturity_date: Mapped[date] = mapped_column(Date)
    repayment_frequency: Mapped[str] = mapped_column(String(12))
    amortization_method: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(12), server_default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[CreatedAt]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LoanRepaymentSchedule(Base):
    __tablename__ = "loan_repayment_schedule"
    __table_args__ = (
        UniqueConstraint("loan_id", "installment_no"),
        Index("ix_loan_repayment_schedule_loan_id_due_date", "loan_id", "due_date"),
    )

    id: Mapped[UUIDPk]
    loan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("loans.id", ondelete="CASCADE"))
    installment_no: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date)
    principal_due: Mapped[Money]
    interest_due: Mapped[Money]


class LoanPayment(Base):
    __tablename__ = "loan_payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_loan_payments_loan_id_paid_on", "loan_id", "paid_on"),
    )

    id: Mapped[UUIDPk]
    loan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("loans.id", ondelete="CASCADE"))
    paid_on: Mapped[date] = mapped_column(Date)
    amount: Mapped[Money]
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[CreatedAt]
