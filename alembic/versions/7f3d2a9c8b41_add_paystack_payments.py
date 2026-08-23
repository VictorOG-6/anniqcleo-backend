"""add Paystack payments and refund lifecycle

Revision ID: 7f3d2a9c8b41
Revises: 02d2b6c44d11
Create Date: 2026-07-14 13:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel


revision: str = "7f3d2a9c8b41"
down_revision: Union[str, Sequence[str], None] = "02d2b6c44d11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'REFUND_PENDING'")

    payment_status = postgresql.ENUM(
        "INITIALIZED",
        "PENDING",
        "SUCCESS",
        "FAILED",
        "ABANDONED",
        "REFUND_PENDING",
        "REFUNDED",
        name="paymentstatus",
        create_type=False,
    )
    refund_status = postgresql.ENUM(
        "PENDING",
        "PROCESSING",
        "NEEDS_ATTENTION",
        "PROCESSED",
        "FAILED",
        name="refundstatus",
        create_type=False,
    )
    payment_status.create(op.get_bind(), checkfirst=True)
    refund_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "order",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "order",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "payment",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "provider_transaction_id",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("amount_kobo", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sqlmodel.sql.sqltypes.AutoString(length=3),
            nullable=False,
        ),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("access_code", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "authorization_url",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["order.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index("ix_payment_order_id", "payment", ["order_id"])
    op.create_index(
        "ix_payment_provider_transaction_id",
        "payment",
        ["provider_transaction_id"],
    )
    op.create_index("ix_payment_reference", "payment", ["reference"], unique=True)

    op.create_table(
        "refund",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider_refund_id",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("amount_kobo", sa.Integer(), nullable=False),
        sa.Column("status", refund_status, nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["payment_id"], ["payment.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("payment_id"),
    )
    op.create_index(
        "ix_refund_provider_refund_id",
        "refund",
        ["provider_refund_id"],
    )

    op.create_table(
        "webhookevent",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fingerprint", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(
        "ix_webhookevent_event_type",
        "webhookevent",
        ["event_type"],
    )
    op.create_index(
        "ix_webhookevent_fingerprint",
        "webhookevent",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_webhookevent_fingerprint", table_name="webhookevent")
    op.drop_index("ix_webhookevent_event_type", table_name="webhookevent")
    op.drop_table("webhookevent")
    op.drop_index("ix_refund_provider_refund_id", table_name="refund")
    op.drop_table("refund")
    op.drop_index("ix_payment_reference", table_name="payment")
    op.drop_index("ix_payment_provider_transaction_id", table_name="payment")
    op.drop_index("ix_payment_order_id", table_name="payment")
    op.drop_table("payment")
    op.drop_column("order", "completed_at")
    op.drop_column("order", "confirmed_at")
    postgresql.ENUM(name="refundstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="paymentstatus").drop(op.get_bind(), checkfirst=True)
    # PostgreSQL cannot safely remove REFUND_PENDING from orderstatus in-place.
