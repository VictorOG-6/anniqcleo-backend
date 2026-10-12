"""add product sub variants

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-27 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "productsubvariant",
        sa.Column("size", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["product_variant_id"], ["productvariant.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(
        "ix_productsubvariant_product_variant_id",
        "productsubvariant",
        ["product_variant_id"],
    )
    op.create_check_constraint(
        "ck_productsubvariant_quantity_nonnegative",
        "productsubvariant",
        "quantity >= 0",
    )

    op.add_column(
        "cartitem",
        sa.Column("product_sub_variant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cartitem_product_sub_variant",
        "cartitem",
        "productsubvariant",
        ["product_sub_variant_id"],
        ["id"],
    )
    op.create_index(
        "ix_cartitem_product_sub_variant_id",
        "cartitem",
        ["product_sub_variant_id"],
    )

    op.add_column(
        "orderitem",
        sa.Column("product_sub_variant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_orderitem_product_sub_variant",
        "orderitem",
        "productsubvariant",
        ["product_sub_variant_id"],
        ["id"],
    )
    op.create_index(
        "ix_orderitem_product_sub_variant_id",
        "orderitem",
        ["product_sub_variant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_orderitem_product_sub_variant_id", table_name="orderitem")
    op.drop_constraint(
        "fk_orderitem_product_sub_variant",
        "orderitem",
        type_="foreignkey",
    )
    op.drop_column("orderitem", "product_sub_variant_id")

    op.drop_index("ix_cartitem_product_sub_variant_id", table_name="cartitem")
    op.drop_constraint(
        "fk_cartitem_product_sub_variant",
        "cartitem",
        type_="foreignkey",
    )
    op.drop_column("cartitem", "product_sub_variant_id")

    op.drop_constraint(
        "ck_productsubvariant_quantity_nonnegative",
        "productsubvariant",
        type_="check",
    )
    op.drop_index(
        "ix_productsubvariant_product_variant_id",
        table_name="productsubvariant",
    )
    op.drop_table("productsubvariant")
