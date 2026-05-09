"""Add APPLYING_PENDING_APPROVAL status

Revision ID: a0828d99fedd
Revises: c6ab10ce906e
Create Date: 2026-05-08 10:17:55.615457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0828d99fedd'
down_revision: Union[str, Sequence[str], None] = 'c6ab10ce906e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'APPLYING_PENDING_APPROVAL'")

def downgrade() -> None:
    """Downgrade schema."""
    pass
