"""add variant order inventory lifecycle

Revision ID: 91c5e7a2b4d8
Revises: 4a82c10d6e31
Create Date: 2026-07-28 10:29:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "91c5e7a2b4d8"
down_revision: Union[str, Sequence[str], None] = "4a82c10d6e31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cartitem",
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cartitem_product_variant",
        "cartitem",
        "productvariant",
        ["product_variant_id"],
        ["id"],
    )
    op.create_index(
        "ix_cartitem_product_variant_id",
        "cartitem",
        ["product_variant_id"],
    )

    op.add_column(
        "orderitem",
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_orderitem_product_variant",
        "orderitem",
        "productvariant",
        ["product_variant_id"],
        ["id"],
    )
    op.create_index(
        "ix_orderitem_product_variant_id",
        "orderitem",
        ["product_variant_id"],
    )

    op.add_column(
        "order",
        sa.Column("inventory_committed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "order",
        sa.Column("inventory_restored_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_check_constraint(
        "ck_product_quantity_nonnegative",
        "product",
        "quantity >= 0",
    )
    op.create_check_constraint(
        "ck_productvariant_quantity_nonnegative",
        "productvariant",
        "quantity >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_productvariant_quantity_nonnegative",
        "productvariant",
        type_="check",
    )
    op.drop_constraint(
        "ck_product_quantity_nonnegative",
        "product",
        type_="check",
    )
    op.drop_column("order", "inventory_restored_at")
    op.drop_column("order", "inventory_committed_at")

    op.drop_index("ix_orderitem_product_variant_id", table_name="orderitem")
    op.drop_constraint(
        "fk_orderitem_product_variant",
        "orderitem",
        type_="foreignkey",
    )
    op.drop_column("orderitem", "product_variant_id")

    op.drop_index("ix_cartitem_product_variant_id", table_name="cartitem")
    op.drop_constraint(
        "fk_cartitem_product_variant",
        "cartitem",
        type_="foreignkey",
    )
    op.drop_column("cartitem", "product_variant_id")
