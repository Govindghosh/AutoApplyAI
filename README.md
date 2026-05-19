# AutoApplyAI

AutoApplyAI is an AI-assisted job application operations platform. It combines a Next.js dashboard, a FastAPI backend, PostgreSQL, Redis, Celery workers, Playwright automation, real-time telemetry, resume processing, workflow supervision, and multi-provider AI routing.

The current repo is built around a supervised automation model: jobs are scraped and analyzed, high-fit roles can be shortlisted, application workflows run as checkpointed backend tasks, and final submission is paused behind explicit human approval.

## What It Does

- Scrapes jobs from the supported source registry: Remotive, Jobicy, Arbeitnow, RemoteOK, Wellfound, LinkedIn, Indeed, Glassdoor, Naukri, Foundit, Shine, TimesJobs, CutShort, and WorkIndia.
- Stores normalized job records and deduplicates them by source ID.
- Analyzes jobs against resume context with AI match scoring.
- Routes AI tasks across OpenAI, Anthropic, Gemini, and OpenRouter with fallback.
- Uploads resumes, extracts text from PDF/DOC/DOCX, and normalizes resume data.
- Lets users review extracted resume fields before syncing them into the profile.
- Tracks job state from scraped to analyzed, shortlisted, applying, pending approval, applied, failed, interview, or rejected.
- Runs application workflows as durable steps with retry, replay, termination, trace export, and recovery hints.
- Emits real-time telemetry through Redis Pub/Sub and WebSockets.
- Provides operations, governance, ATS capability, reliability, and intelligence dashboards.
- Enforces beta safety controls such as daily application limits, concurrency limits, and final submit approval.

## Architecture

![Architecture](./architecture.png)

```text
Next.js frontend
  -> FastAPI API
  -> PostgreSQL for durable state
  -> Redis for Celery broker/results and telemetry Pub/Sub
  -> Celery workers for scraping, AI analysis, resume processing, and workflows
  -> Playwright/ATS adapters for browser automation
  -> AI provider router for OpenAI, Anthropic, Gemini, and OpenRouter
  -> n8n through backend-emitted webhooks for notifications and ops integrations
```

## Tech Stack

Frontend:

- Next.js 16
- React 19
- TypeScript
- Tailwind CSS
- TanStack React Query
- Axios
- Lucide icons

Backend:

- FastAPI
- SQLAlchemy
- Pydantic v2
- Alembic
- JWT auth
- Celery
- Redis
- PostgreSQL
- Playwright

AI and automation:

- OpenAI API
- Anthropic Claude API
- Google Gemini API
- OpenRouter API
- Playwright Chromium
- ATS adapters for Greenhouse and Lever

Operations:

- Docker Compose
- Flower for Celery monitoring
- PgAdmin for database inspection
- n8n for external notification, reporting, and integration automation

## Repository Layout

```text
AutoApplyAI/
|-- README.md
|-- architecture.png
|-- docker-compose.yml
|-- infra/
|   `-- n8n/
|-- storage/
|-- backend/
|   |-- Dockerfile
|   |-- requirements.txt
|   |-- alembic/
|   |-- tests/
|   `-- app/
|       |-- api/
|       |-- automation/
|       |-- core/
|       |-- models/
|       |-- resume/
|       |-- schemas/
|       |-- scraper/
|       |-- services/
|       |-- utils/
|       `-- workers/
`-- frontend/
    |-- package.json
    |-- next.config.ts
    |-- src/
    |   |-- app/
    |   |-- components/
    |   |-- lib/
    |   `-- providers/
    `-- public/
```

## Backend Modules

Core:

- `backend/app/main.py`: FastAPI app, CORS, health endpoints, API router registration, dev schema sync.
- `backend/app/core/config.py`: environment-driven settings.
- `backend/app/core/database.py`: SQLAlchemy engine and sessions.
- `backend/app/core/security.py`: password hashing and token helpers.

API routes:

- `/api/v1/auth`: register, login, refresh, logout, current user, export, purge.
- `/api/v1/jobs`: list jobs, scrape, analyze, analyze scraped jobs, start workflow, finalize submission.
- `/api/v1/profiles`: profile read/create/update and resume association.
- `/api/v1/profiles/resumes`: resume upload, review, retry, delete, approve extracted fields.
- `/api/v1/workflows`: workflow details, step retry, replay, report, terminate, resolve.
- `/api/v1/ws`: telemetry WebSocket and event history.
- `/api/v1/intelligence`: application outcomes and performance insights.
- `/api/v1/operations`: SLOs, safety limits, observability, reliability, chaos trigger.
- `/api/v1/transparency`: trace export and product telemetry events.
- `/api/v1/governance`: recommendation review, approve, reject, rollback.
- `/api/v1/orchestration`: trust profile and calibration events.
- `/api/v1/ats`: ATS capability matrix, risk dashboard, policies, certification.
- `/api/v1/team-governance`: operator roles, locks, assignments, approval chains, incidents.

Services:

- `AIService`: provider routing and structured JSON/text generation.
- `JobService`: job persistence and deduplication.
- `ResumeService`: PDF/DOC/DOCX extraction, AI normalization, local fallback parsing.
- `WorkflowOrchestrator`: checkpointed application workflow graph.
- `StateManager`: job state transitions and telemetry.
- `IntelligenceService`: source performance, score correlation, resume performance, insights.
- `SafetyThrottleService`: beta application/concurrency limits.
- `RecoveryService`, `EscalationService`, `WorkflowExplainability`: recovery hints and supervised workflow UX.
- `GovernanceService`, `TeamGovernanceService`, `ATSCapabilityService`: operational review and platform governance.
- `PatternAnalysisService`, `SignalIntegrityService`, `ReliabilityScalingService`, `ReliabilityOptimizationService`: operations dashboard inputs.

Workers:

- `scrape_jobs_task`: runs every scraper registered in `backend/app/automation/scrapers/registry.py`.
- `analyze_job_task`: runs multi-provider AI analysis and updates match score/status.
- `apply_to_job_task`: initializes or resumes workflow steps and pauses before final submit.
- `process_resume_task`: extracts and normalizes resume content, then marks review status.

## Frontend Screens

The dashboard lives under `frontend/src/app/(dashboard)`.

- `/dashboard`: overview metrics for scraped jobs, applications, interviews, and match rate.
- `/jobs`: Mission Control for scraping, analysis, shortlisting, workflow start, approval, failed-analysis retry.
- `/profile`: professional context, skills, roles, locations, salary, and resume-backed profile data.
- `/resumes`: resume upload and extraction pipeline.
- `/resumes/review/[id]`: field-by-field resume extraction review and profile sync.
- `/applications`: application history.
- `/intelligence`: outcome analytics, source performance, score correlation, resume performance, recommendations.
- `/operations`: orchestration health, safety, observability, supportability, governance, reliability.
- `/settings`: system and account settings.
- `/login`, `/register`, `/onboarding`: auth and onboarding flows.

Shared frontend systems:

- `TelemetryProvider`: connects to backend WebSocket telemetry and keeps event history.
- `LiveMissionControl`: floating live event monitor.
- `WorkflowSupervisor`: side panel for workflow steps, recovery hints, replay, trace export, report, terminate.
- `backend-api.ts`: typed frontend API client.

## AI Provider Routing

AI is centralized in `backend/app/services/ai_service.py`.

Provider keys are optional. Blank keys are skipped. If a configured provider fails because of quota, invalid key, parsing, or a runtime error, the task falls back to the next configured provider.

Default task order:

| Task | Provider order |
| --- | --- |
| Job analysis | OpenAI -> Anthropic -> Gemini -> OpenRouter |
| Resume normalization | Gemini -> OpenAI -> Anthropic -> OpenRouter |
| Generic job parsing | Gemini -> OpenAI -> OpenRouter -> Anthropic |
| Resume optimization | Anthropic -> OpenAI -> Gemini -> OpenRouter |
| General | OpenAI -> Anthropic -> Gemini -> OpenRouter |

Default model selectors:

```env
OPENAI_MODEL=gpt-5.4-mini
GEMINI_MODEL=gemini-2.5-flash
OPENROUTER_MODEL=openai/gpt-5.4-mini
ANTHROPIC_MODEL=claude-sonnet-4-6
```

The worker stores the successful provider/model descriptor in `jobs.last_analysis_model`, for example `openai:gpt-5.4-mini`.

## Job State Machine

Primary job states:

```text
SCRAPED
ANALYSIS_PENDING
ANALYZING
ANALYZED
ANALYSIS_FAILED
SHORTLISTED
READY_TO_APPLY
APPLYING
APPLYING_PENDING_APPROVAL
APPLIED
FAILED
INTERVIEW
REJECTED
```

The final submit checkpoint intentionally transitions to `APPLYING_PENDING_APPROVAL` until the user approves it from Mission Control.

## Workflow Steps

Application workflows are modeled as ordered checkpoints:

```text
NAVIGATE_TO_JOB
AUTH_CHECK
UPLOAD_RESUME
FILL_BASIC_INFO
HANDLE_CUSTOM_QUESTIONS
SUBMIT_APPLICATION
VERIFY_SUBMISSION
```

Current workflow execution is scaffolded for supervised automation. Some handlers are placeholders, but the state, telemetry, replay, pause, approval, and failure recovery surfaces are implemented.

## Environment Variables

Backend settings are read from `backend/.env`.

Minimum local backend configuration:

```env
PROJECT_NAME=AutoApplyAI
ENVIRONMENT=dev
DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/autoapplyai
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

JWT_SECRET_KEY=change-this-to-at-least-32-characters
JWT_REFRESH_SECRET_KEY=change-this-too-at-least-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=false
COOKIE_HTTP_ONLY=true
COOKIE_SAMESITE=lax

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-5.4-mini
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6

N8N_WEBHOOK_URL=http://n8n:5678/webhook/autoapplyai-events
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=ap-south-1
S3_BUCKET_NAME=

PLAYWRIGHT_HEADLESS=true
LOG_LEVEL=INFO
```

Important notes:

- `DEBUG` must be `true` or `false`; values like `release` will fail Pydantic validation.
- `JWT_SECRET_KEY` and `JWT_REFRESH_SECRET_KEY` must be at least 32 characters.
- In Docker Compose, use service hostnames such as `db` and `redis` in URLs.
- In Docker Compose, use `http://n8n:5678/webhook/autoapplyai-events` for the n8n webhook URL.
- For manual local backend execution outside Docker, use `http://localhost:5678/webhook/autoapplyai-events` instead.
- For manual local backend execution outside Docker, use `localhost` in database and Redis URLs.
- Runtime uploads and browser session state are stored in repo-root `storage/`, mounted into backend and Celery containers at `/app/storage`.
- Do not commit real API keys.

Frontend configuration is read from `NEXT_PUBLIC_*` variables:

```env
NEXT_PUBLIC_APP_NAME=AutoApplyAI
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
NEXT_PUBLIC_WS_URL=
NEXT_PUBLIC_TELEMETRY_RECONNECT_MS=5000
NEXT_PUBLIC_TELEMETRY_EVENT_LIMIT=50
NEXT_PUBLIC_WORKFLOW_REFRESH_MS=2000
NEXT_PUBLIC_OPERATIONS_REFRESH_MS=5000
NEXT_PUBLIC_DAILY_APPLICATION_LIMIT=5
NEXT_PUBLIC_WORKFLOW_CONCURRENCY_LIMIT=5
NEXT_PUBLIC_ALLOWED_RESUME_EXTENSIONS=.pdf,.doc,.docx
NEXT_PUBLIC_MAX_RESUME_MB=10
NEXT_PUBLIC_DEFAULT_CURRENCY=USD
NEXT_PUBLIC_CURRENCY_OPTIONS=USD,INR
NEXT_PUBLIC_REMOTE_OPTIONS=Remote,Hybrid,On-site
```

If `NEXT_PUBLIC_WS_URL` is blank, the frontend derives the WebSocket base URL from `NEXT_PUBLIC_API_URL`.

## Local Development

### Option 1: Docker for backend dependencies and backend services

From the repository root:

```powershell
docker compose up --build
```

This starts:

- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- PgAdmin on `http://localhost:5050`
- FastAPI backend on `http://localhost:8000`
- Celery worker
- Flower on `http://localhost:5555`

The compose file does not start the Next.js frontend. Run it separately:

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`.

### Option 2: Manual backend

Start PostgreSQL and Redis first, then:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
alembic upgrade head
uvicorn app.main:app --reload
```

Run a Celery worker in another terminal:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
celery -A app.workers.celery_app worker --loglevel=info
```

Run Flower if needed:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
celery -A app.workers.celery_app flower
```

### Manual frontend

```powershell
cd frontend
npm install
npm run dev
```

## Useful URLs

- Frontend: `http://localhost:3000`
- Backend root: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/health`
- Flower: `http://localhost:5555`
- PgAdmin: `http://localhost:5050`

## Database

Alembic migrations live in `backend/alembic/versions`.

Useful commands:

```powershell
cd backend
alembic upgrade head
alembic revision --autogenerate -m "describe_change"
```

The FastAPI startup also calls `Base.metadata.create_all()` for dev convenience, but migrations should still be treated as the durable schema history.

## Testing and Quality

Backend tests:

```powershell
cd backend
$env:DEBUG="true"
.\venv\Scripts\python.exe -m pytest
```

Frontend lint:

```powershell
cd frontend
npm run lint
```

Current backend tests cover:

- Orchestration personalization policy compression.
- ATS certification capability contract.
- Team governance lock auditing.
- AI provider routing and fallback behavior.

## Common Workflows

Scrape jobs:

1. Open Mission Control.
2. Click `Find Matches`.
3. Celery runs every registered job source scraper.
4. New jobs are saved with `SCRAPED` status.

Analyze jobs:

1. Click `Analyze Matches` or analyze a single scraped job.
2. Celery runs `analyze_job_task`.
3. `AIService` chooses the best configured provider for job analysis.
4. Jobs scoring at least 75 are auto-shortlisted.
5. Failures are stored in `analysis_error` and can be retried from Mission Control.

Apply to a shortlisted job:

1. Click `Start Workflow`.
2. Backend creates or resumes an `ApplicationWorkflow`.
3. Steps run through the orchestrator.
4. `SUBMIT_APPLICATION` pauses for explicit approval.
5. Click `Approve Final Submit` to resume the workflow.

Resume ingestion:

1. Upload a PDF/DOC/DOCX resume.
2. Celery extracts text and asks AI to normalize fields.
3. If AI fails, local parsing fallback is used.
4. Review extracted fields.
5. Approve selected fields to sync into the profile.

n8n webhook automation:

1. Start n8n with `docker compose up -d n8n`.
2. Open `http://localhost:5678` and complete the first-time n8n account setup.
3. Import `/files/autoapplyai-event-webhook.json` from inside the n8n container, or import `infra/n8n/autoapplyai-event-webhook.json` from this repo.
4. Save and activate the workflow.
5. Keep `N8N_WEBHOOK_URL=http://n8n:5678/webhook/autoapplyai-events` for Docker Compose backend/celery.
6. Verify from the backend API with `POST /api/v1/operations/n8n/test`.

n8n is intentionally an integration layer only. The FastAPI backend remains the orchestration source of truth for workflow state, checkpoints, retries, ATS adapters, browser automation, governance, and replay semantics. n8n workflows should handle external notifications, incident routing, reporting, digests, and integration exports.

## Troubleshooting

`ANALYSIS_FAILED`:

- Check the job card in Mission Control for `analysis_error`.
- Most common causes are quota, invalid API key, unavailable model, or malformed AI JSON.
- The router will try other configured providers automatically.
- After fixing keys/quota/model settings, click `Retry Analysis`.

Backend config fails on startup:

- Confirm `DEBUG=true` or `DEBUG=false`.
- Confirm JWT secrets are at least 32 characters.
- Confirm `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, and `CELERY_RESULT_BACKEND` are set.

Frontend cannot reach API:

- Confirm backend is running on `http://localhost:8000`.
- Confirm `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1`.
- Confirm CORS origins in backend settings include the frontend URL.

Telemetry disconnected:

- Confirm Redis is running.
- Confirm the user is logged in and `access_token` exists in local storage.
- Confirm the WebSocket URL resolves to `/api/v1/ws/telemetry?token=...`.

Celery task does not run:

- Confirm Redis is running.
- Confirm `celery_worker` container or manual worker is running.
- Check Flower at `http://localhost:5555`.

Playwright failures:

- In Docker, the backend image installs Chromium and dependencies.
- Locally, run `playwright install chromium`.
- Keep `PLAYWRIGHT_HEADLESS=true` for non-interactive worker runs.

## Current Limitations

- The browser application workflow is checkpointed and supervised, but several concrete form-filling handlers are still placeholders.
- LinkedIn direct integration is not implemented in this repo.
- The Docker Compose stack does not include the frontend service.
- The Gemini integration currently uses the existing `google-generativeai` package in the repo; the newer `google.genai` package is not installed yet.

## Roadmap Ideas

- Production frontend container in Docker Compose.
- Complete ATS-specific form filling for Greenhouse, Lever, and more platforms.
- Provider health dashboard for AI quota/key/model failures.
- Cover letter generation and resume variant generation.
- Email and calendar follow-up automation.
- More outcome-driven strategy recommendations.
- CI workflow for backend tests and frontend lint.

## Author

Govind Ghosh

Full Stack Product Engineer  
FastAPI, React, Redis, Docker, AWS, Automation
