"""add extra fields

Revision ID: e8bdb93d7ac4
Revises: ecb0bea9e608
Create Date: 2026-06-09 20:32:10.749982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8bdb93d7ac4'
down_revision: Union[str, Sequence[str], None] = 'ecb0bea9e608'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    userrole = sa.Enum('USER', 'ADMIN', 'STAFF', name='userrole')
    userrole.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'user',
        sa.Column(
            'role',
            userrole,
            nullable=False,
            server_default='USER',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user', 'role')
    sa.Enum('USER', 'ADMIN', 'STAFF', name='userrole').drop(
        op.get_bind(),
        checkfirst=True,
    )
