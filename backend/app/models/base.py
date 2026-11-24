import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from sqlalchemy import JSON, DateTime, MetaData, Numeric, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


JSONType = JSON().with_variant(JSONB(), "postgresql")

# Reusable column types. All money/quantity/price values are exact Decimals, never floats.
UUIDPk = Annotated[uuid.UUID, mapped_column(Uuid, primary_key=True, default=uuid.uuid4)]
CreatedAt = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now())]
Money = Annotated[Decimal, mapped_column(Numeric(18, 2))]
Price = Annotated[Decimal, mapped_column(Numeric(18, 6))]
Quantity = Annotated[Decimal, mapped_column(Numeric(24, 8))]
Rate = Annotated[Decimal, mapped_column(Numeric(7, 4))]
