"""initial schema

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _id():
    return sa.Column("id", sa.Uuid(), nullable=False)


def _created():
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _updated():
    return sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def _fk(col, target, ondelete, nullable=False):
    return sa.Column(col, sa.Uuid(), sa.ForeignKey(target, ondelete=ondelete), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "users", _id(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _created(),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("email"),
    )
    op.create_table(
        "user_settings",
        _fk("user_id", "users.id", "CASCADE"),
        sa.Column("theme", sa.String(10), server_default="dark", nullable=False),
        sa.Column("currency", sa.String(3), server_default="SEK", nullable=False),
        sa.Column("dashboard_layout", JSONType),
        sa.Column("loan_amortization_method", sa.String(20), server_default="annuity", nullable=False),
        sa.Column("ai_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ai_external_sharing_consent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("paper_starting_cash", sa.Numeric(18, 2), server_default="100000", nullable=False),
        _updated(),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(64), nullable=False),
        _fk("user_id", "users.id", "CASCADE"),
        sa.Column("csrf_token", sa.String(64), nullable=False),
        _created(),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(45)),
        sa.Column("user_agent", sa.String(255)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])

    op.create_table(
        "borrowers", _id(), _fk("user_id", "users.id", "CASCADE"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320)), sa.Column("phone", sa.String(50)),
        sa.Column("notes", sa.Text()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        _created(), _updated(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_borrowers_user_id_name", "borrowers", ["user_id", "name"])

    op.create_table(
        "loans", _id(), _fk("user_id", "users.id", "CASCADE"), _fk("borrower_id", "borrowers.id", "RESTRICT"),
        sa.Column("principal", sa.Numeric(18, 2), nullable=False),
        sa.Column("annual_interest_rate", sa.Numeric(7, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="SEK", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date(), nullable=False),
        sa.Column("repayment_frequency", sa.String(12), nullable=False),
        sa.Column("amortization_method", sa.String(20), nullable=False),
        sa.Column("status", sa.String(12), server_default="active", nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        _created(), _updated(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("principal > 0", name="principal_positive"),
        sa.CheckConstraint("annual_interest_rate >= 0", name="rate_non_negative"),
        sa.CheckConstraint("maturity_date > start_date", name="maturity_after_start"),
    )
    op.create_index("ix_loans_user_id_status", "loans", ["user_id", "status"])
    op.create_index("ix_loans_borrower_id", "loans", ["borrower_id"])

    op.create_table(
        "loan_repayment_schedule", _id(), _fk("loan_id", "loans.id", "CASCADE"),
        sa.Column("installment_no", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("principal_due", sa.Numeric(18, 2), nullable=False),
        sa.Column("interest_due", sa.Numeric(18, 2), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("loan_id", "installment_no"),
    )
    op.create_index("ix_loan_repayment_schedule_loan_id_due_date", "loan_repayment_schedule", ["loan_id", "due_date"])

    op.create_table(
        "loan_payments", _id(), _fk("loan_id", "loans.id", "CASCADE"),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("note", sa.String(500)),
        _created(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount > 0", name="amount_positive"),
    )
    op.create_index("ix_loan_payments_loan_id_paid_on", "loan_payments", ["loan_id", "paid_on"])

    op.create_table(
        "watchlists", _id(), _fk("user_id", "users.id", "CASCADE"),
        sa.Column("name", sa.String(100), nullable=False), _created(),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id", "name"),
    )
    op.create_table(
        "watchlist_instruments", _id(), _fk("watchlist_id", "watchlists.id", "CASCADE"),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200)), sa.Column("exchange", sa.String(32)),
        _created(),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("watchlist_id", "symbol"),
    )
    op.create_table(
        "market_data_cache", _id(),
        sa.Column("cache_key", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("data_type", sa.String(32), nullable=False),
        sa.Column("payload", JSONType, nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("cache_key"),
    )
    op.create_index("ix_market_data_cache_symbol_data_type", "market_data_cache", ["symbol", "data_type"])

    op.create_table(
        "paper_accounts", _id(), _fk("user_id", "users.id", "CASCADE"),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("starting_cash", sa.Numeric(18, 2), nullable=False),
        sa.Column("cash_balance", sa.Numeric(18, 2), nullable=False),
        _created(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("cash_balance >= 0", name="cash_non_negative"),
    )
    op.create_index("ix_paper_accounts_user_id", "paper_accounts", ["user_id"])

    op.create_table(
        "paper_orders", _id(), _fk("account_id", "paper_accounts.id", "CASCADE"),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("order_type", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("limit_price", sa.Numeric(18, 6)),
        sa.Column("status", sa.String(12), server_default="pending", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True)),
        sa.Column("fill_price", sa.Numeric(18, 6)),
        sa.Column("is_simulated", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("side IN ('buy','sell')", name="side_valid"),
        sa.CheckConstraint("order_type IN ('market','limit')", name="type_valid"),
        sa.CheckConstraint("quantity > 0", name="quantity_positive"),
        sa.CheckConstraint("is_simulated IS TRUE", name="always_simulated"),
    )
    op.create_index("ix_paper_orders_account_id_submitted_at", "paper_orders", ["account_id", "submitted_at"])

    op.create_table(
        "paper_positions", _id(), _fk("account_id", "paper_accounts.id", "CASCADE"),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("avg_entry_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(18, 2), server_default="0", nullable=False),
        _updated(),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("account_id", "symbol"),
        sa.CheckConstraint("quantity >= 0", name="quantity_non_negative"),
    )
    op.create_table(
        "paper_trades", _id(), _fk("account_id", "paper_accounts.id", "CASCADE"),
        _fk("order_id", "paper_orders.id", "SET NULL", nullable=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("fees", sa.Numeric(18, 2), server_default="0", nullable=False),
        sa.Column("realized_pnl", sa.Numeric(18, 2)),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("is_simulated IS TRUE", name="always_simulated"),
    )
    op.create_index("ix_paper_trades_account_id_executed_at", "paper_trades", ["account_id", "executed_at"])

    op.create_table(
        "notifications", _id(), _fk("user_id", "users.id", "CASCADE"),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        _created(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id_read_at_created_at", "notifications", ["user_id", "read_at", "created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        _fk("user_id", "users.id", "SET NULL", nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64)), sa.Column("entity_id", sa.String(64)),
        sa.Column("ip", sa.String(45)),
        sa.Column("details", JSONType),
        _created(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_id_created_at", "audit_logs", ["user_id", "created_at"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    for table in (
        "audit_logs", "notifications", "paper_trades", "paper_positions", "paper_orders",
        "paper_accounts", "market_data_cache", "watchlist_instruments", "watchlists",
        "loan_payments", "loan_repayment_schedule", "loans", "borrowers", "sessions",
        "user_settings", "users",
    ):
        op.drop_table(table)
