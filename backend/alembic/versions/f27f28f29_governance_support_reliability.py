"""Add governance review tables

Revision ID: f27f28f29
Revises: b1e53c8ead7f
Create Date: 2026-05-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f27f28f29"
down_revision: Union[str, Sequence[str], None] = "b1e53c8ead7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


recommendation_status = sa.Enum(
    "PENDING_REVIEW",
    "APPROVED",
    "REJECTED",
    "ROLLED_BACK",
    name="recommendationstatus",
)


def upgrade() -> None:
    recommendation_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "operational_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("source_signal", sa.String(), nullable=True),
        sa.Column("recommendation_type", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("target_policy", sa.String(), nullable=True),
        sa.Column("proposed_change", sa.JSON(), nullable=True),
        sa.Column("rollback_plan", sa.JSON(), nullable=True),
        sa.Column("explainability", sa.JSON(), nullable=True),
        sa.Column("shadow_evaluation", sa.JSON(), nullable=True),
        sa.Column("status", recommendation_status, nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("implemented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operational_recommendations_id"), "operational_recommendations", ["id"], unique=False)
    op.create_index(op.f("ix_operational_recommendations_recommendation_type"), "operational_recommendations", ["recommendation_type"], unique=False)
    op.create_index(op.f("ix_operational_recommendations_reviewer_id"), "operational_recommendations", ["reviewer_id"], unique=False)
    op.create_index(op.f("ix_operational_recommendations_source_signal"), "operational_recommendations", ["source_signal"], unique=False)
    op.create_index(op.f("ix_operational_recommendations_status"), "operational_recommendations", ["status"], unique=False)
    op.create_index(op.f("ix_operational_recommendations_user_id"), "operational_recommendations", ["user_id"], unique=False)

    op.create_table(
        "governance_timeline_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("recommendation_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column("outcome_metrics", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["recommendation_id"], ["operational_recommendations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_governance_timeline_entries_action"), "governance_timeline_entries", ["action"], unique=False)
    op.create_index(op.f("ix_governance_timeline_entries_actor_user_id"), "governance_timeline_entries", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_governance_timeline_entries_id"), "governance_timeline_entries", ["id"], unique=False)
    op.create_index(op.f("ix_governance_timeline_entries_recommendation_id"), "governance_timeline_entries", ["recommendation_id"], unique=False)
    op.create_index(op.f("ix_governance_timeline_entries_user_id"), "governance_timeline_entries", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_governance_timeline_entries_user_id"), table_name="governance_timeline_entries")
    op.drop_index(op.f("ix_governance_timeline_entries_recommendation_id"), table_name="governance_timeline_entries")
    op.drop_index(op.f("ix_governance_timeline_entries_id"), table_name="governance_timeline_entries")
    op.drop_index(op.f("ix_governance_timeline_entries_actor_user_id"), table_name="governance_timeline_entries")
    op.drop_index(op.f("ix_governance_timeline_entries_action"), table_name="governance_timeline_entries")
    op.drop_table("governance_timeline_entries")

    op.drop_index(op.f("ix_operational_recommendations_user_id"), table_name="operational_recommendations")
    op.drop_index(op.f("ix_operational_recommendations_status"), table_name="operational_recommendations")
    op.drop_index(op.f("ix_operational_recommendations_source_signal"), table_name="operational_recommendations")
    op.drop_index(op.f("ix_operational_recommendations_reviewer_id"), table_name="operational_recommendations")
    op.drop_index(op.f("ix_operational_recommendations_recommendation_type"), table_name="operational_recommendations")
    op.drop_index(op.f("ix_operational_recommendations_id"), table_name="operational_recommendations")
    op.drop_table("operational_recommendations")
    recommendation_status.drop(op.get_bind(), checkfirst=True)
