from fastapi import APIRouter
from app.api.routes import auth, jobs, profiles, resumes, intelligence, events, workflows, operations, transparency

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
