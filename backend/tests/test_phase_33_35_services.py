import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./phase_33_35_test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "abcdefghijklmnopqrstuvwxyz123456")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "abcdefghijklmnopqrstuvwxyz123456")
os.environ.setdefault("DEBUG", "true")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import *  # noqa: F401,F403
from app.models.job import Job
from app.models.personalization import ExplainabilityLevel, OrchestrationTrustMode, RecoveryGuidanceMode
from app.models.user import User
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.ats_capability_service import ATSCapabilityService
from app.services.personalization_service import OrchestrationPersonalizationService
from app.services.team_governance_service import TeamGovernanceService


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def seed_workflow(db_session):
    user = User(email="owner@example.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()
    job = Job(
        source_id="job-1",
        title="Backend Engineer",
        company="Example",
        url="https://example.com/job",
        source="Workday",
    )
    db_session.add(job)
    db_session.flush()
    workflow = ApplicationWorkflow(job_id=job.id, user_id=user.id, platform_type="Workday")
    db_session.add(workflow)
    db_session.flush()
    step = WorkflowStep(
        workflow_id=workflow.id,
        name="VERIFY_SUBMISSION",
        status=WorkflowStatus.FAILED,
        error_log="captcha verification required",
        attempts=1,
    )
    db_session.add(step)
    db_session.commit()
    return user, workflow, step


def test_personalization_profile_compresses_visibility_not_execution(db_session):
    user, workflow, step = seed_workflow(db_session)

    profile = OrchestrationPersonalizationService.update_profile(
        db_session,
        user.id,
        {
            "trust_mode": OrchestrationTrustMode.AGGRESSIVE,
            "explainability_level": ExplainabilityLevel.BASIC,
            "recovery_guidance_mode": RecoveryGuidanceMode.BEGINNER,
            "minimal_explainability": True,
            "max_replay_suggestions_per_workflow": 99,
        },
    )

    policy = OrchestrationPersonalizationService.effective_policy(profile)
    guidance = OrchestrationPersonalizationService.personalize_recovery_guidance(
        workflow,
        step,
        {"action": "manual_escalation", "confidence": 0.86, "safety_validated": True, "replay_scope": "manual_resume"},
        profile,
    )

    assert policy["trust_mode"] == OrchestrationTrustMode.AGGRESSIVE.value
    assert policy["max_replay_suggestions_per_workflow"] == 3
    assert policy["immutable_governance"]["mandatory_final_approval"] is True
    assert "site requested verification" in guidance["message"]
    assert guidance["mutation_allowed"] is False


def test_ats_certification_requires_capability_contract(db_session):
    seed_workflow(db_session)

    run = ATSCapabilityService.certify_adapter(db_session, "Workday", actor_user_id=1)
    dashboard = ATSCapabilityService.build_dashboard(db_session)

    workday = next(item for item in dashboard["capability_matrix"] if item["platform"] == "Workday")
    assert run["status"] == "PASSED"
    assert run["score"] == 100
    assert workday["adapter_status"] == "CERTIFIED"
    assert workday["policy"]["supervision_posture"] == "conservative"


def test_team_governance_lock_conflicts_are_audited(db_session):
    owner, workflow, _ = seed_workflow(db_session)
    operator = User(email="operator@example.com", password_hash="hash")
    db_session.add(operator)
    db_session.commit()

    TeamGovernanceService.ensure_owner_role(db_session, owner.id)
    lock = TeamGovernanceService.acquire_lock(db_session, workflow, owner.id)

    with pytest.raises(Exception):
        TeamGovernanceService.assert_no_conflicting_lock(db_session, workflow, operator.id)

    dashboard = TeamGovernanceService.build_dashboard(db_session, owner.id, owner.id)
    assert lock["workflow_id"] == workflow.id
    assert dashboard["metrics"]["governance_audit_completeness"] > 0
