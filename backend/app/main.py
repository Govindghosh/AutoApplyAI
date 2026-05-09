from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AutoApplyAI backend...")
    
    # Ensure all tables exist (simplified migrations for dev)
    try:
        from app.core.database import engine, Base
        # Explicitly import models so they are registered with Base
        from app.models.user import User
        from app.models.job import Job
        from app.models.profile import UserProfile, Resume
        from app.models.event import SystemEvent
        from app.models.outcome import ApplicationOutcome
        from app.models.workflow import ApplicationWorkflow, WorkflowStep
        from app.models.health import SelectorHealth
        
        logger.info("Syncing database schema...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema sync complete.")
    except Exception as e:
        logger.error(f"Database schema sync failed: {e}")
        # We continue so health checks can still pass if needed, 
        # or it will fail later on actual DB access.
    
    yield
    logger.info("Shutting down AutoApplyAI backend...")


def create_app() -> FastAPI:
    setup_logging()
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ==========================================
    # CORS
    # ==========================================
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ==========================================
    # ROOT ENDPOINT
    # ==========================================
    @app.get("/")
    async def root():
        return {
            "message": "AutoApplyAI Backend Running",
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
        }

    # ==========================================
    # HEALTH CHECK
    # ==========================================
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
        }

    # ==========================================
    # ROUTERS
    # ==========================================
    from app.api.routes import auth, jobs, profiles, resumes, events
    from app.api.api import api_router
    
    # We include events and auth separately if they are not in api_router, 
    # but based on the previous edits, it's better to stay consistent.
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()