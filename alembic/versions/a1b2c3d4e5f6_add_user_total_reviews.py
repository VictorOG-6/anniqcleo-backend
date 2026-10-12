"""add user total_reviews

Revision ID: a1b2c3d4e5f6
Revises: cff431885d3f
Create Date: 2026-08-24 16:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'cff431885d3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user', sa.Column('total_reviews', sa.Integer(), nullable=False, server_default='0'))
    op.execute(
        """
        UPDATE "user"
        SET total_reviews = (
            SELECT COUNT(*)
            FROM review
            WHERE review.user_id = "user".id
        )
        """
    )
    op.alter_column('user', 'total_reviews', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user', 'total_reviews')
