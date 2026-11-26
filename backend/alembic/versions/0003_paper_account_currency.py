"""paper accounts: currency

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("paper_accounts", sa.Column("currency", sa.String(3), server_default="SEK", nullable=False))
    op.create_check_constraint("currency_length", "paper_accounts", "length(currency) = 3")


def downgrade() -> None:
    op.drop_constraint("currency_length", "paper_accounts", type_="check")
    op.drop_column("paper_accounts", "currency")
