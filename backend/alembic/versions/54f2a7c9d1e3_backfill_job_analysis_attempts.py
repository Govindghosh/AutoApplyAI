"""Backfill job analysis attempts

Revision ID: 54f2a7c9d1e3
Revises: ac33e34e35
Create Date: 2026-05-11 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "54f2a7c9d1e3"
down_revision: Union[str, Sequence[str], None] = "ac33e34e35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Normalize existing jobs and prevent future NULL attempts."""
    op.execute("UPDATE jobs SET analysis_attempts = 0 WHERE analysis_attempts IS NULL")
    op.alter_column(
        "jobs",
        "analysis_attempts",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("0"),
    )


def downgrade() -> None:
    """Allow NULL attempts again."""
    op.alter_column(
        "jobs",
        "analysis_attempts",
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )
