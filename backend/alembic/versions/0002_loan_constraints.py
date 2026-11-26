"""loans: borrower must belong to the same user, and valid frequency, method, status and currency

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

FREQUENCIES = "'weekly','biweekly','monthly','quarterly','semiannual','annual'"
METHODS = "'annuity','equal_principal','interest_only'"
STATUSES = "'active','repaid','closed'"


def upgrade() -> None:
    op.create_unique_constraint("uq_borrowers_id_user_id", "borrowers", ["id", "user_id"])

    # Replace the single-column borrower FK with one that also pins user_id. The old FK is looked up
    # by its columns rather than its name, so this works whichever name the first migration produced.
    for fk in sa.inspect(op.get_bind()).get_foreign_keys("loans"):
        if fk["referred_table"] == "borrowers" and fk["constrained_columns"] == ["borrower_id"]:
            op.drop_constraint(fk["name"], "loans", type_="foreignkey")
    op.create_foreign_key(
        "fk_loans_borrower_same_user", "loans", "borrowers",
        ["borrower_id", "user_id"], ["id", "user_id"], ondelete="RESTRICT",
    )

    op.create_check_constraint("frequency_valid", "loans", f"repayment_frequency IN ({FREQUENCIES})")
    op.create_check_constraint("method_valid", "loans", f"amortization_method IN ({METHODS})")
    op.create_check_constraint("status_valid", "loans", f"status IN ({STATUSES})")
    op.create_check_constraint("currency_length", "loans", "length(currency) = 3")


def downgrade() -> None:
    for name in ("currency_length", "status_valid", "method_valid", "frequency_valid"):
        op.drop_constraint(name, "loans", type_="check")
    op.drop_constraint("fk_loans_borrower_same_user", "loans", type_="foreignkey")
    op.create_foreign_key("fk_loans_borrower_id_borrowers", "loans", "borrowers", ["borrower_id"], ["id"], ondelete="RESTRICT")
    op.drop_constraint("uq_borrowers_id_user_id", "borrowers", type_="unique")
