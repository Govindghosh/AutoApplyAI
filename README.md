# AutoApplyAI

AI-powered remote job automation platform built using Next.js, FastAPI, Redis, PostgreSQL, Celery, Docker, and Playwright.

AutoApplyAI helps engineers automate the remote job application pipeline through intelligent job scraping, AI-based job analysis, resume customization, application tracking, and browser automation workflows.

---

# System Architecture

![Architecture](./architecture.png)

---

# Core Features

## Job Aggregation Engine
- Scrapes remote jobs from multiple platforms
- Supports async scraping workflows
- Removes duplicate job listings
- Normalizes job metadata

## AI Job Analysis
- Match score generation
- ATS keyword extraction
- Missing skill detection
- Resume recommendation engine

## Resume Management
- Multiple resume versions
- Resume upload & storage
- AI-powered keyword optimization
- Dynamic PDF generation

## Application Automation
- Browser automation using Playwright
- Auto-fill application workflows
- Human approval before submission
- Status tracking system

## Real-Time Dashboard
- Live application tracking
- Job pipeline monitoring
- Response analytics
- WebSocket-powered updates

## Background Workers
- Celery worker architecture
- Redis queue processing
- Scheduled scraping jobs
- Async task execution

---

# Tech Stack

## Frontend
- Next.js
- TypeScript
- Tailwind CSS
- React Query

## Backend
- FastAPI
- SQLAlchemy
- Pydantic
- JWT Authentication

## Infrastructure
- Docker
- Nginx
- GitHub Actions
- AWS EC2

## Database & Queues
- PostgreSQL
- Redis
- Celery

## Automation & AI
- Playwright
- OpenAI / Gemini APIs

---

# Project Structure

```bash
AutoApplyAI/
│
├── frontend/
├── backend/
├── infra/
├── docs/
├── screenshots/
├── scripts/
│
├── docker-compose.yml
├── README.md
└── architecture.png
```

---

# Backend Structure

```bash
backend/
│
├── app/
│   ├── api/
│   ├── auth/
│   ├── jobs/
│   ├── resumes/
│   ├── ai/
│   ├── workers/
│   ├── scraper/
│   ├── db/
│   ├── models/
│   └── services/
│
├── alembic/
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

# Frontend Structure

```bash
frontend/
│
├── app/
├── components/
├── services/
├── hooks/
├── types/
├── lib/
├── middleware.ts
└── Dockerfile
```

---

# Core Workflow

```text
User Dashboard
      ↓
FastAPI Backend
      ↓
Job Scraper Service
      ↓
Redis Queue
      ↓
Celery Workers
      ↓
AI Analysis Engine
      ↓
Resume Optimization
      ↓
Playwright Automation
      ↓
Application Tracking
```

---

# Local Development Setup

## Clone Repository

```bash
git clone https://github.com/Govindghosh/AutoApplyAI.git
cd AutoApplyAI
```

---

# Start Docker Services

```bash
docker compose up --build
```

---

# Backend Setup

```bash
cd backend

python -m venv venv

source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run server:

```bash
uvicorn app.main:app --reload
```

---

# Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

---

# Environment Variables

## Backend

```env
DATABASE_URL=
REDIS_URL=
OPENAI_API_KEY=
JWT_SECRET=
AWS_ACCESS_KEY=
AWS_SECRET_KEY=
```

---

# Planned Features

- LinkedIn direct integrations
- AI cover letter generation
- Referral discovery engine
- Email automation workflows
- Analytics dashboard
- Multi-agent AI workflows
- Interview preparation engine

---

# Infrastructure Goals

- Production-ready Docker setup
- CI/CD pipelines using GitHub Actions
- Scalable async worker architecture
- Cloud deployment on AWS EC2
- Monitoring & logging stack
- Automated backups

---

# Why This Project Exists

Most job application workflows are repetitive, inefficient, and poorly optimized.

AutoApplyAI aims to combine:
- AI analysis
- browser automation
- infrastructure engineering
- async processing
- scalable backend systems

into a unified engineering platform.

---

# License

MIT License

---

# Author

Govind Ghosh

Full Stack Product Engineer  
FastAPI • React • Redis • Docker • AWS • Automation