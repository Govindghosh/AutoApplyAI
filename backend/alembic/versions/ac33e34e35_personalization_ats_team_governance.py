"""Add personalization, ATS capability, and team governance tables

Revision ID: ac33e34e35
Revises: f27f28f29
Create Date: 2026-05-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ac33e34e35"
down_revision: Union[str, Sequence[str], None] = "f27f28f29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


orchestration_trust_mode = sa.Enum("CONSERVATIVE", "BALANCED", "AGGRESSIVE", name="orchestrationtrustmode")
explainability_level = sa.Enum("BASIC", "TECHNICAL", "OPERATIONAL", name="explainabilitylevel")
recovery_guidance_mode = sa.Enum("BEGINNER", "ADVANCED", name="recoveryguidancemode")
ats_adapter_status = sa.Enum("PLANNED", "SANDBOX", "CERTIFIED", "DISABLED", name="atsadapterstatus")
ats_certification_status = sa.Enum("PENDING", "PASSED", "FAILED", name="atscertificationstatus")
operator_role = sa.Enum("USER", "REVIEWER", "SUPPORT_OPERATOR", "ADMIN", "AUDITOR", name="operatorrole")
approval_chain_status = sa.Enum("PENDING", "APPROVED", "REJECTED", name="approvalchainstatus")
incident_status = sa.Enum("OPEN", "IN_PROGRESS", "RESOLVED", name="incidentstatus")


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in [
        orchestration_trust_mode,
        explainability_level,
        recovery_guidance_mode,
        ats_adapter_status,
        ats_certification_status,
        operator_role,
        approval_chain_status,
        incident_status,
    ]:
        enum_type.create(bind, checkfirst=True)

    op.add_column("selector_health", sa.Column("drift_severity", sa.String(), nullable=True))
    op.add_column("selector_health", sa.Column("drift_classification", sa.JSON(), nullable=True))
    op.create_index(op.f("ix_selector_health_drift_severity"), "selector_health", ["drift_severity"], unique=False)

    op.create_table(
        "orchestration_trust_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("trust_mode", orchestration_trust_mode, nullable=True),
        sa.Column("explainability_level", explainability_level, nullable=True),
        sa.Column("recovery_guidance_mode", recovery_guidance_mode, nullable=True),
        sa.Column("verbose_explainability", sa.Boolean(), nullable=True),
        sa.Column("minimal_explainability", sa.Boolean(), nullable=True),
        sa.Column("escalation_batching", sa.Boolean(), nullable=True),
        sa.Column("grouped_approvals", sa.Boolean(), nullable=True),
        sa.Column("interruption_sensitivity", sa.String(), nullable=True),
        sa.Column("replay_auto_suggestions", sa.Boolean(), nullable=True),
        sa.Column("captcha_handling_preference", sa.String(), nullable=True),
        sa.Column("max_replay_suggestions_per_workflow", sa.Integer(), nullable=True),
        sa.Column("preference_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_orchestration_trust_profiles_id"), "orchestration_trust_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_orchestration_trust_profiles_trust_mode"), "orchestration_trust_profiles", ["trust_mode"], unique=False)
    op.create_index(op.f("ix_orchestration_trust_profiles_user_id"), "orchestration_trust_profiles", ["user_id"], unique=True)

    op.create_table(
        "trust_calibration_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=True),
        sa.Column("step_id", sa.Integer(), nullable=True),
        sa.Column("event_name", sa.String(), nullable=True),
        sa.Column("profile_mode", sa.String(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("value", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["step_id"], ["workflow_steps.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["application_workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trust_calibration_events_created_at"), "trust_calibration_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_trust_calibration_events_event_name"), "trust_calibration_events", ["event_name"], unique=False)
    op.create_index(op.f("ix_trust_calibration_events_id"), "trust_calibration_events", ["id"], unique=False)
    op.create_index(op.f("ix_trust_calibration_events_profile_mode"), "trust_calibration_events", ["profile_mode"], unique=False)
    op.create_index(op.f("ix_trust_calibration_events_step_id"), "trust_calibration_events", ["step_id"], unique=False)
    op.create_index(op.f("ix_trust_calibration_events_user_id"), "trust_calibration_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_trust_calibration_events_workflow_id"), "trust_calibration_events", ["workflow_id"], unique=False)

    op.create_table(
        "ats_capability_matrix",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("adapter_name", sa.String(), nullable=True),
        sa.Column("adapter_status", ats_adapter_status, nullable=True),
        sa.Column("autofill_stability", sa.Float(), nullable=True),
        sa.Column("replay_safety", sa.Float(), nullable=True),
        sa.Column("drift_frequency", sa.Float(), nullable=True),
        sa.Column("escalation_rate", sa.Float(), nullable=True),
        sa.Column("submission_confidence", sa.Float(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("operational_risk", sa.String(), nullable=True),
        sa.Column("policy", sa.JSON(), nullable=True),
        sa.Column("capability_notes", sa.JSON(), nullable=True),
        sa.Column("last_scored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform"),
    )
    op.create_index(op.f("ix_ats_capability_matrix_adapter_status"), "ats_capability_matrix", ["adapter_status"], unique=False)
    op.create_index(op.f("ix_ats_capability_matrix_id"), "ats_capability_matrix", ["id"], unique=False)
    op.create_index(op.f("ix_ats_capability_matrix_operational_risk"), "ats_capability_matrix", ["operational_risk"], unique=False)
    op.create_index(op.f("ix_ats_capability_matrix_platform"), "ats_capability_matrix", ["platform"], unique=True)

    op.create_table(
        "ats_certification_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("adapter_name", sa.String(), nullable=True),
        sa.Column("status", ats_certification_status, nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("checks", sa.JSON(), nullable=True),
        sa.Column("report", sa.JSON(), nullable=True),
        sa.Column("certified_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ats_certification_runs_certified_by_user_id"), "ats_certification_runs", ["certified_by_user_id"], unique=False)
    op.create_index(op.f("ix_ats_certification_runs_id"), "ats_certification_runs", ["id"], unique=False)
    op.create_index(op.f("ix_ats_certification_runs_platform"), "ats_certification_runs", ["platform"], unique=False)
    op.create_index(op.f("ix_ats_certification_runs_status"), "ats_certification_runs", ["status"], unique=False)

    op.create_table(
        "team_operator_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("operator_user_id", sa.Integer(), nullable=False),
        sa.Column("role", operator_role, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_team_operator_roles_id"), "team_operator_roles", ["id"], unique=False)
    op.create_index(op.f("ix_team_operator_roles_operator_user_id"), "team_operator_roles", ["operator_user_id"], unique=False)
    op.create_index(op.f("ix_team_operator_roles_owner_user_id"), "team_operator_roles", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_team_operator_roles_role"), "team_operator_roles", ["role"], unique=False)

    op.create_table(
        "workflow_oversight_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_operator_id", sa.Integer(), nullable=False),
        sa.Column("assigned_role", operator_role, nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_operator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["application_workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_oversight_assignments_assigned_operator_id"), "workflow_oversight_assignments", ["assigned_operator_id"], unique=False)
    op.create_index(op.f("ix_workflow_oversight_assignments_id"), "workflow_oversight_assignments", ["id"], unique=False)
    op.create_index(op.f("ix_workflow_oversight_assignments_owner_user_id"), "workflow_oversight_assignments", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_workflow_oversight_assignments_status"), "workflow_oversight_assignments", ["status"], unique=False)
    op.create_index(op.f("ix_workflow_oversight_assignments_workflow_id"), "workflow_oversight_assignments", ["workflow_id"], unique=False)

    op.create_table(
        "workflow_locks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("locked_by_user_id", sa.Integer(), nullable=False),
        sa.Column("lock_scope", sa.String(), nullable=True),
        sa.Column("lock_token", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["locked_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["application_workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lock_token"),
    )
    op.create_index(op.f("ix_workflow_locks_created_at"), "workflow_locks", ["created_at"], unique=False)
    op.create_index(op.f("ix_workflow_locks_id"), "workflow_locks", ["id"], unique=False)
    op.create_index(op.f("ix_workflow_locks_lock_scope"), "workflow_locks", ["lock_scope"], unique=False)
    op.create_index(op.f("ix_workflow_locks_lock_token"), "workflow_locks", ["lock_token"], unique=True)
    op.create_index(op.f("ix_workflow_locks_workflow_id"), "workflow_locks", ["workflow_id"], unique=False)

    op.create_table(
        "governance_approval_chains",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("required_roles", sa.JSON(), nullable=True),
        sa.Column("approvals", sa.JSON(), nullable=True),
        sa.Column("status", approval_chain_status, nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_governance_approval_chains_action"), "governance_approval_chains", ["action"], unique=False)
    op.create_index(op.f("ix_governance_approval_chains_created_by_user_id"), "governance_approval_chains", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_governance_approval_chains_id"), "governance_approval_chains", ["id"], unique=False)
    op.create_index(op.f("ix_governance_approval_chains_owner_user_id"), "governance_approval_chains", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_governance_approval_chains_resource_id"), "governance_approval_chains", ["resource_id"], unique=False)
    op.create_index(op.f("ix_governance_approval_chains_resource_type"), "governance_approval_chains", ["resource_type"], unique=False)
    op.create_index(op.f("ix_governance_approval_chains_status"), "governance_approval_chains", ["status"], unique=False)

    op.create_table(
        "incident_threads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("status", incident_status, nullable=True),
        sa.Column("assigned_operator_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_operator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["application_workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incident_threads_assigned_operator_id"), "incident_threads", ["assigned_operator_id"], unique=False)
    op.create_index(op.f("ix_incident_threads_id"), "incident_threads", ["id"], unique=False)
    op.create_index(op.f("ix_incident_threads_owner_user_id"), "incident_threads", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_incident_threads_severity"), "incident_threads", ["severity"], unique=False)
    op.create_index(op.f("ix_incident_threads_status"), "incident_threads", ["status"], unique=False)
    op.create_index(op.f("ix_incident_threads_workflow_id"), "incident_threads", ["workflow_id"], unique=False)

    op.create_table(
        "incident_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("annotation_type", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["incident_id"], ["incident_threads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incident_comments_actor_user_id"), "incident_comments", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_incident_comments_annotation_type"), "incident_comments", ["annotation_type"], unique=False)
    op.create_index(op.f("ix_incident_comments_id"), "incident_comments", ["id"], unique=False)
    op.create_index(op.f("ix_incident_comments_incident_id"), "incident_comments", ["incident_id"], unique=False)

    op.create_table(
        "workflow_intervention_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=True),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workflow_id"], ["application_workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflow_intervention_audits_action"), "workflow_intervention_audits", ["action"], unique=False)
    op.create_index(op.f("ix_workflow_intervention_audits_actor_user_id"), "workflow_intervention_audits", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_workflow_intervention_audits_created_at"), "workflow_intervention_audits", ["created_at"], unique=False)
    op.create_index(op.f("ix_workflow_intervention_audits_id"), "workflow_intervention_audits", ["id"], unique=False)
    op.create_index(op.f("ix_workflow_intervention_audits_owner_user_id"), "workflow_intervention_audits", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_workflow_intervention_audits_workflow_id"), "workflow_intervention_audits", ["workflow_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_intervention_audits_workflow_id"), table_name="workflow_intervention_audits")
    op.drop_index(op.f("ix_workflow_intervention_audits_owner_user_id"), table_name="workflow_intervention_audits")
    op.drop_index(op.f("ix_workflow_intervention_audits_id"), table_name="workflow_intervention_audits")
    op.drop_index(op.f("ix_workflow_intervention_audits_created_at"), table_name="workflow_intervention_audits")
    op.drop_index(op.f("ix_workflow_intervention_audits_actor_user_id"), table_name="workflow_intervention_audits")
    op.drop_index(op.f("ix_workflow_intervention_audits_action"), table_name="workflow_intervention_audits")
    op.drop_table("workflow_intervention_audits")

    op.drop_index(op.f("ix_incident_comments_incident_id"), table_name="incident_comments")
    op.drop_index(op.f("ix_incident_comments_id"), table_name="incident_comments")
    op.drop_index(op.f("ix_incident_comments_annotation_type"), table_name="incident_comments")
    op.drop_index(op.f("ix_incident_comments_actor_user_id"), table_name="incident_comments")
    op.drop_table("incident_comments")

    op.drop_index(op.f("ix_incident_threads_workflow_id"), table_name="incident_threads")
    op.drop_index(op.f("ix_incident_threads_status"), table_name="incident_threads")
    op.drop_index(op.f("ix_incident_threads_severity"), table_name="incident_threads")
    op.drop_index(op.f("ix_incident_threads_owner_user_id"), table_name="incident_threads")
    op.drop_index(op.f("ix_incident_threads_id"), table_name="incident_threads")
    op.drop_index(op.f("ix_incident_threads_assigned_operator_id"), table_name="incident_threads")
    op.drop_table("incident_threads")

    op.drop_index(op.f("ix_governance_approval_chains_status"), table_name="governance_approval_chains")
    op.drop_index(op.f("ix_governance_approval_chains_resource_type"), table_name="governance_approval_chains")
    op.drop_index(op.f("ix_governance_approval_chains_resource_id"), table_name="governance_approval_chains")
    op.drop_index(op.f("ix_governance_approval_chains_owner_user_id"), table_name="governance_approval_chains")
    op.drop_index(op.f("ix_governance_approval_chains_id"), table_name="governance_approval_chains")
    op.drop_index(op.f("ix_governance_approval_chains_created_by_user_id"), table_name="governance_approval_chains")
    op.drop_index(op.f("ix_governance_approval_chains_action"), table_name="governance_approval_chains")
    op.drop_table("governance_approval_chains")

    op.drop_index(op.f("ix_workflow_locks_workflow_id"), table_name="workflow_locks")
    op.drop_index(op.f("ix_workflow_locks_lock_token"), table_name="workflow_locks")
    op.drop_index(op.f("ix_workflow_locks_lock_scope"), table_name="workflow_locks")
    op.drop_index(op.f("ix_workflow_locks_id"), table_name="workflow_locks")
    op.drop_index(op.f("ix_workflow_locks_created_at"), table_name="workflow_locks")
    op.drop_table("workflow_locks")

    op.drop_index(op.f("ix_workflow_oversight_assignments_workflow_id"), table_name="workflow_oversight_assignments")
    op.drop_index(op.f("ix_workflow_oversight_assignments_status"), table_name="workflow_oversight_assignments")
    op.drop_index(op.f("ix_workflow_oversight_assignments_owner_user_id"), table_name="workflow_oversight_assignments")
    op.drop_index(op.f("ix_workflow_oversight_assignments_id"), table_name="workflow_oversight_assignments")
    op.drop_index(op.f("ix_workflow_oversight_assignments_assigned_operator_id"), table_name="workflow_oversight_assignments")
    op.drop_table("workflow_oversight_assignments")

    op.drop_index(op.f("ix_team_operator_roles_role"), table_name="team_operator_roles")
    op.drop_index(op.f("ix_team_operator_roles_owner_user_id"), table_name="team_operator_roles")
    op.drop_index(op.f("ix_team_operator_roles_operator_user_id"), table_name="team_operator_roles")
    op.drop_index(op.f("ix_team_operator_roles_id"), table_name="team_operator_roles")
    op.drop_table("team_operator_roles")

    op.drop_index(op.f("ix_ats_certification_runs_status"), table_name="ats_certification_runs")
    op.drop_index(op.f("ix_ats_certification_runs_platform"), table_name="ats_certification_runs")
    op.drop_index(op.f("ix_ats_certification_runs_id"), table_name="ats_certification_runs")
    op.drop_index(op.f("ix_ats_certification_runs_certified_by_user_id"), table_name="ats_certification_runs")
    op.drop_table("ats_certification_runs")

    op.drop_index(op.f("ix_ats_capability_matrix_platform"), table_name="ats_capability_matrix")
    op.drop_index(op.f("ix_ats_capability_matrix_operational_risk"), table_name="ats_capability_matrix")
    op.drop_index(op.f("ix_ats_capability_matrix_id"), table_name="ats_capability_matrix")
    op.drop_index(op.f("ix_ats_capability_matrix_adapter_status"), table_name="ats_capability_matrix")
    op.drop_table("ats_capability_matrix")

    op.drop_index(op.f("ix_trust_calibration_events_workflow_id"), table_name="trust_calibration_events")
    op.drop_index(op.f("ix_trust_calibration_events_user_id"), table_name="trust_calibration_events")
    op.drop_index(op.f("ix_trust_calibration_events_step_id"), table_name="trust_calibration_events")
    op.drop_index(op.f("ix_trust_calibration_events_profile_mode"), table_name="trust_calibration_events")
    op.drop_index(op.f("ix_trust_calibration_events_id"), table_name="trust_calibration_events")
    op.drop_index(op.f("ix_trust_calibration_events_event_name"), table_name="trust_calibration_events")
    op.drop_index(op.f("ix_trust_calibration_events_created_at"), table_name="trust_calibration_events")
    op.drop_table("trust_calibration_events")

    op.drop_index(op.f("ix_orchestration_trust_profiles_user_id"), table_name="orchestration_trust_profiles")
    op.drop_index(op.f("ix_orchestration_trust_profiles_trust_mode"), table_name="orchestration_trust_profiles")
    op.drop_index(op.f("ix_orchestration_trust_profiles_id"), table_name="orchestration_trust_profiles")
    op.drop_table("orchestration_trust_profiles")

    op.drop_index(op.f("ix_selector_health_drift_severity"), table_name="selector_health")
    op.drop_column("selector_health", "drift_classification")
    op.drop_column("selector_health", "drift_severity")

    bind = op.get_bind()
    for enum_type in [
        incident_status,
        approval_chain_status,
        operator_role,
        ats_certification_status,
        ats_adapter_status,
        recovery_guidance_mode,
        explainability_level,
        orchestration_trust_mode,
    ]:
        enum_type.drop(bind, checkfirst=True)
