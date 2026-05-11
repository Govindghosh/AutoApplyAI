from fastapi import APIRouter
from app.api.routes import (
    ats,
    auth,
    events,
    governance,
    intelligence,
    jobs,
    operations,
    orchestration,
    profiles,
    resumes,
    team_governance,
    transparency,
    workflows,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(profiles.router)
api_router.include_router(resumes.router)
api_router.include_router(intelligence.router)
api_router.include_router(events.router)
api_router.include_router(workflows.router)
api_router.include_router(operations.router)
api_router.include_router(transparency.router)
api_router.include_router(governance.router)
api_router.include_router(orchestration.router)
api_router.include_router(ats.router)
api_router.include_router(team_governance.router)
