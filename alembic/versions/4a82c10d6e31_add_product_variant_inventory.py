"""add product and variant inventory

Revision ID: 4a82c10d6e31
Revises: e15ee533a6cd
Create Date: 2026-07-27 13:24:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a82c10d6e31"
down_revision: Union[str, Sequence[str], None] = "e15ee533a6cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "product",
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "productvariant",
        sa.Column("name", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "productvariant",
        sa.Column("image_url", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "productvariant",
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
    )

    op.execute(
        """
        UPDATE product
        SET quantity = variant_totals.quantity
        FROM (
            SELECT product_id, SUM(quantity) AS quantity
            FROM productvariant
            GROUP BY product_id
        ) AS variant_totals
        WHERE product.id = variant_totals.product_id
        """
    )

    op.alter_column("product", "quantity", server_default=None)
    op.alter_column("productvariant", "name", server_default=None)
    op.alter_column("productvariant", "image_url", server_default=None)
    op.alter_column("productvariant", "quantity", server_default=None)


def downgrade() -> None:
    op.drop_column("productvariant", "quantity")
    op.drop_column("productvariant", "image_url")
    op.drop_column("productvariant", "name")
    op.drop_column("product", "quantity")
