"""add order_items and cart_items

Revision ID: 95afb3fb377d
Revises: e8bdb93d7ac4
Create Date: 2026-06-13 20:29:20.833505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '95afb3fb377d'
down_revision: Union[str, Sequence[str], None] = 'e8bdb93d7ac4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('order', sa.Column('public_id', sa.String(), nullable=True))
    op.add_column('product', sa.Column('slug', sa.String(), nullable=True))

    op.execute(
        """
        WITH ordered_orders AS (
            SELECT id, row_number() OVER (ORDER BY created_at, id) AS order_number
            FROM "order"
            WHERE public_id IS NULL
        )
        UPDATE "order"
        SET public_id = 'ord-' || lpad(ordered_orders.order_number::text, 4, '0')
        FROM ordered_orders
        WHERE "order".id = ordered_orders.id
        """
    )
    op.execute(
        """
        UPDATE product
        SET slug = regexp_replace(lower(name), '[^a-z0-9]+', '-', 'g')
            || '-' || left(id::text, 8)
        WHERE slug IS NULL
        """
    )

    op.alter_column('order', 'public_id', nullable=False)
    op.alter_column('product', 'slug', nullable=False)
    op.create_index(op.f('ix_order_public_id'), 'order', ['public_id'], unique=True)
    op.create_index(op.f('ix_product_slug'), 'product', ['slug'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_product_slug'), table_name='product')
    op.drop_column('product', 'slug')
    op.drop_index(op.f('ix_order_public_id'), table_name='order')
    op.drop_column('order', 'public_id')
