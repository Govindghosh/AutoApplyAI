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
from pydantic import SecretStr

from app.core.database import Base
from app.models import *  # noqa: F401,F403
from app.models.job import Job
from app.models.profile import Resume, UserProfile
from app.models.personalization import (
    ExplainabilityLevel,
    OrchestrationTrustMode,
    RecoveryGuidanceMode,
)
from app.models.user import User
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.services.ai_service import AIService
from app.services.ats_capability_service import ATSCapabilityService
from app.services.auth_service import AuthService
from app.services.job_matching_service import JobMatchingService
from app.services.job_service import JobFilters, JobService
from app.services.personalization_service import OrchestrationPersonalizationService
from app.services.team_governance_service import TeamGovernanceService
from app.schemas.user import UserCreate, UserLogin
from app.utils.n8n import N8NClient


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
    workflow = ApplicationWorkflow(
        job_id=job.id, user_id=user.id, platform_type="Workday"
    )
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
        {
            "action": "manual_escalation",
            "confidence": 0.86,
            "safety_validated": True,
            "replay_scope": "manual_resume",
        },
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

    workday = next(
        item for item in dashboard["capability_matrix"] if item["platform"] == "Workday"
    )
    assert run["status"] == "PASSED"
    assert run["score"] == 100
    assert workday["adapter_status"] == "CERTIFIED"
    assert workday["policy"]["supervision_posture"] == "conservative"


def test_refresh_token_rotates_and_keeps_session_valid(db_session):
    user = AuthService.register_user(
        db_session,
        UserCreate(email="refresh@example.com", password="strong-password"),
    )
    tokens = AuthService.authenticate_user(
        db_session,
        UserLogin(email="refresh@example.com", password="strong-password"),
    )

    refreshed = AuthService.refresh_token(db_session, tokens["refresh_token"])

    assert refreshed["access_token"]
    assert refreshed["refresh_token"]
    assert refreshed["refresh_token"] != tokens["refresh_token"]
    assert AuthService.verify_access_token(refreshed["access_token"]) == str(user.id)


def test_n8n_client_skips_when_not_configured():
    result = N8NClient(webhook_url="").trigger_event("TEST", {"ok": True})

    assert result.configured is False
    assert result.delivered is False


def test_n8n_client_posts_event_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        text = '{"ok": true}'

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.utils.n8n.requests.post", fake_post)

    result = N8NClient(
        webhook_url="http://n8n:5678/webhook/autoapplyai-events"
    ).trigger_event(
        "JOB_ANALYZED",
        {"job_id": 123},
    )

    assert result.configured is True
    assert result.delivered is True
    assert captured["url"] == "http://n8n:5678/webhook/autoapplyai-events"
    assert captured["json"]["event"] == "JOB_ANALYZED"
    assert captured["json"]["payload"]["job_id"] == 123


def test_team_governance_lock_conflicts_are_audited(db_session):
    owner, workflow, _ = seed_workflow(db_session)
    operator = User(email="operator@example.com", password_hash="hash")
    db_session.add(operator)
    db_session.commit()

    TeamGovernanceService.ensure_owner_role(db_session, owner.id)
    lock = TeamGovernanceService.acquire_lock(db_session, workflow, owner.id)

    with pytest.raises(Exception):
        TeamGovernanceService.assert_no_conflicting_lock(
            db_session, workflow, operator.id
        )

    dashboard = TeamGovernanceService.build_dashboard(db_session, owner.id, owner.id)
    assert lock["workflow_id"] == workflow.id
    assert dashboard["metrics"]["governance_audit_completeness"] > 0


def test_job_list_uses_base_resume_domain_filter(db_session):
    user = User(email="backend@example.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()

    profile = UserProfile(
        user_id=user.id,
        title="Backend Developer",
        preferred_roles=["Backend Engineer"],
        skills=["Python", "FastAPI", "PostgreSQL"],
        tech_stack={"backend": ["FastAPI"], "database": ["PostgreSQL"]},
    )
    db_session.add(profile)
    db_session.flush()

    resume = Resume(
        profile_id=profile.id,
        name="Base Resume",
        content_text="Backend Developer with Python, FastAPI, PostgreSQL, Docker, and REST API experience.",
        is_base=True,
    )
    db_session.add(resume)

    backend_job = Job(
        source_id="backend-1",
        title="Backend Engineer",
        company="API Co",
        description="Build Python FastAPI services backed by PostgreSQL.",
        url="https://example.com/backend",
        source="RemoteOK",
    )
    design_job = Job(
        source_id="design-1",
        title="Product Designer",
        company="Studio",
        description="Own Figma prototypes, UX research, and visual design systems.",
        url="https://example.com/design",
        source="RemoteOK",
    )
    db_session.add_all([backend_job, design_job])
    db_session.commit()

    jobs = JobService.get_jobs_for_user(db_session, user.id)
    filtered_jobs = JobService.get_jobs_for_user(
        db_session,
        user.id,
        filters=JobFilters(source="RemoteOK", search="FastAPI", remote_type="all"),
    )
    source_summary = JobService.get_source_summary_for_user(db_session, user.id)
    context = JobMatchingService.build_context(db_session, user.id)

    assert [job.source_id for job in jobs] == ["backend-1"]
    assert [job.source_id for job in filtered_jobs] == ["backend-1"]
    assert (
        next(item for item in source_summary if item["source"] == "RemoteOK")["count"]
        == 1
    )
    assert (
        next(item for item in source_summary if item["source"] == "Indeed")["supported"]
        is True
    )
    assert context.base_resume_id == resume.id
    assert "FastAPI" in JobMatchingService.resume_text_for_analysis(context)


def test_scraper_search_query_prioritizes_profile_current_title(db_session):
    user = User(email="title-first@example.com", password_hash="hash")
    db_session.add(user)
    db_session.flush()

    profile = UserProfile(
        user_id=user.id,
        title="QA Automation Engineer",
        preferred_roles=["Senior Backend Platform Engineer"],
        skills=["Python", "FastAPI", "PostgreSQL"],
    )
    db_session.add(profile)
    db_session.commit()

    context = JobMatchingService.build_context(db_session, user.id)

    assert context.current_title == "qa automation engineer"
    assert (
        JobMatchingService.search_query_for_scrapers(context)
        == "qa automation engineer"
    )


def test_supported_scrapers_include_major_job_portals():
    from app.automation.scrapers.registry import build_scrapers, supported_source_names

    scrapers = build_scrapers("Backend Engineer", "Remote", 1)

    assert [scraper.source_name for scraper in scrapers] == [
        "Remotive",
        "Jobicy",
        "Arbeitnow",
        "RemoteOK",
        "Wellfound",
        "LinkedIn",
        "Indeed",
        "Glassdoor",
        "Naukri",
        "Foundit",
        "Shine",
        "TimesJobs",
        "CutShort",
        "WorkIndia",
    ]
    assert supported_source_names() == [scraper.source_name for scraper in scrapers]


def test_job_normalization_rejects_low_quality_placeholders():
    jobs = JobService.normalize_jobs(
        [
            {
                "source_id": "bad-1",
                "title": "Recommended Jobs For You",
                "company": "Unknown",
                "url": "https://example.com/search",
                "source": "Glassdoor",
                "description": "Upload your CV and create job alert.",
            },
            {
                "source_id": "good-1",
                "title": "Backend Engineer",
                "company": "Example API",
                "url": "https://example.com/jobs/backend-engineer",
                "source": "Remotive",
                "description": "Build Python APIs with FastAPI, PostgreSQL, Redis, Docker, and production observability.",
                "location": "Remote",
            },
        ]
    )

    assert len(jobs) == 1
    assert jobs[0].source == "Remotive"
    assert jobs[0].raw_data["quality"]["score"] >= 45


@pytest.mark.asyncio
async def test_ai_service_routes_by_task_and_falls_back(monkeypatch):
    import app.services.ai_service as ai_module

    monkeypatch.setattr(ai_module.settings, "OPENAI_API_KEY", SecretStr("openai-key"))
    monkeypatch.setattr(
        ai_module.settings, "ANTHROPIC_API_KEY", SecretStr("anthropic-key")
    )
    monkeypatch.setattr(ai_module.settings, "GEMINI_API_KEY", SecretStr("gemini-key"))
    monkeypatch.setattr(
        ai_module.settings, "OPENROUTER_API_KEY", SecretStr("openrouter-key")
    )

    calls = []

    async def fake_call_provider(self, provider, prompt, response_format, max_tokens):
        calls.append(provider)
        if provider == "openai":
            raise RuntimeError("quota exhausted")
        return """
        {
            "match_score": 82,
            "skills_match": 80,
            "experience_match": 85,
            "location_match": 90,
            "tech_stack_match": 75,
            "missing_keywords": ["Kafka"],
            "resume_improvements": ["Add message queue experience"],
            "risk_level": "medium",
            "justification": "Good backend fit with one missing keyword."
        }
        """

    monkeypatch.setattr(AIService, "_call_provider", fake_call_provider)

    service = AIService()
    analysis = await service.analyze_job(
        "Backend Engineer",
        "Python, FastAPI, PostgreSQL, Kafka",
        "Python, FastAPI, PostgreSQL",
    )

    assert calls == ["openai", "anthropic"]
    assert analysis.match_score == 82
    assert service.last_model_descriptor == "anthropic:claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_ai_service_uses_local_job_analysis_when_provider_credits_fail(
    monkeypatch,
):
    import app.services.ai_service as ai_module

    monkeypatch.setattr(ai_module.settings, "OPENAI_API_KEY", SecretStr("openai-key"))
    monkeypatch.setattr(
        ai_module.settings, "ANTHROPIC_API_KEY", SecretStr("anthropic-key")
    )
    monkeypatch.setattr(ai_module.settings, "GEMINI_API_KEY", SecretStr("gemini-key"))
    monkeypatch.setattr(
        ai_module.settings, "OPENROUTER_API_KEY", SecretStr("openrouter-key")
    )

    async def fake_call_provider(self, provider, prompt, response_format, max_tokens):
        raise RuntimeError("quota exhausted")

    monkeypatch.setattr(AIService, "_call_provider", fake_call_provider)

    service = AIService()
    analysis = await service.analyze_job(
        "Backend Engineer",
        "Build Python FastAPI services with PostgreSQL, Redis, Docker, and AWS.",
        "Backend Developer with Python, FastAPI, PostgreSQL, Docker, and REST API experience.",
    )

    assert service.last_model_descriptor == "local:deterministic-match"
    assert analysis.match_score > 50
    assert "Local fallback used" in analysis.justification
