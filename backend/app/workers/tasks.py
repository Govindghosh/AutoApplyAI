import time
import asyncio
from app.workers.celery_app import celery_app
from app.core.logging import logger
from app.core.database import SessionLocal
from app.models.job import Job, JobStatus
from app.services.job_service import JobService
from app.automation.scrapers.remote_ok import RemoteOKScraper
from app.automation.browser.session_manager import SessionManager
from app.automation.browser.form_handler import FormHandler
from playwright.async_api import async_playwright

@celery_app.task(name="app.workers.tasks.scrape_jobs_task")
def scrape_jobs_task():
    logger.info("Starting multi-source background scraping task...")
    from app.automation.scrapers.remote_ok import RemoteOKScraper
    from app.automation.scrapers.wellfound import WellfoundScraper
    
    scrapers = [RemoteOKScraper(), WellfoundScraper()]
    total_new = 0
    
    for scraper in scrapers:
        try:
            logger.info(f"Running scraper: {scraper.source}")
            jobs = asyncio.run(scraper.scrape())
            if jobs:
                db = SessionLocal()
                try:
                    new_count = JobService.save_jobs(db, jobs)
                    total_new += new_count
                    logger.info(f"Source {scraper.source} produced {new_count} new jobs")
                finally:
                    db.close()
        except Exception as e:
            logger.error(f"Scraper {scraper.source} failed: {e}")
            
    return {"status": "success", "total_new_jobs": total_new}

from datetime import datetime, timezone
from app.services.ai_service import AIService
from app.services.event_service import EventService, EventType

@celery_app.task(
    name="app.workers.tasks.analyze_job_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def analyze_job_task(self, job_id: int, user_id: int, resume_text: str = "Experienced Backend Developer with FastAPI, Docker, and PostgreSQL skills."):
    logger.info(f"Starting analysis for job {job_id}")
    db = SessionLocal()
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
            
        # Emit Analyzing Event
        EventService.emit(user_id, EventType.JOB_ANALYZING, {"job_id": job_id, "title": job.title}, resource_id=str(job_id))
        
        # Cost Control: Skip if already analyzed
        if job.status == JobStatus.ANALYZED and job.ai_analysis:
            logger.info(f"Job {job_id} already analyzed, skipping")
            return
            
        # State Transition: ANALYZING
        job.status = JobStatus.ANALYZING
        job.analysis_attempts += 1
        db.commit()
        
        ai_service = AIService()
        
        # Run async AI call in sync Celery task
        try:
            analysis = asyncio.run(ai_service.analyze_job(
                job_title=job.title,
                job_description=job.description,
                resume_text=resume_text
            ))
        except Exception as e:
            logger.error(f"AI Service call failed for job {job_id}: {e}")
            raise e # Trigger Celery retry

        if not analysis:
            raise Exception("AI returned empty or invalid analysis")

        # Success State Transition
        job.ai_score = analysis.match_score
        job.ai_analysis = analysis.model_dump()
        
        # Decision Engine: Auto-shortlist based on score threshold
        if job.ai_score >= 75.0:
            job.status = JobStatus.SHORTLISTED
            logger.info(f"Job {job_id} auto-shortlisted (Score: {job.ai_score})")
        else:
            job.status = JobStatus.ANALYZED
            
        job.analyzed_at = datetime.now(timezone.utc)
        job.last_analysis_model = "gemini-1.5-flash"
        job.analysis_error = None
        db.commit()
        
        # Emit Analyzed Event
        EventService.emit(user_id, EventType.JOB_ANALYZED, {"job_id": job_id, "score": job.ai_score}, resource_id=str(job_id))
        
        logger.info(f"Successfully analyzed job {job_id} - Score: {job.ai_score}")
        return {"job_id": job_id, "status": "analyzed", "score": job.ai_score}

    except Exception as e:
        db.rollback()
        # Handle failure
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.ANALYSIS_FAILED
            job.analysis_error = str(e)
            db.commit()
            
        logger.warning(f"Retrying analysis for job {job_id} due to error: {e}")
        try:
            self.retry(exc=e)
        except Exception:
            # Max retries reached
            logger.error(f"Max retries reached for job {job_id}")
            
    finally:
        db.close()

@celery_app.task(name="app.workers.tasks.apply_to_job_task", bind=True)
def apply_to_job_task(self, job_id: int, user_id: int):
    """
    Orchestrates the autonomous application flow using the Workflow Graph.
    This replaces monolithic execution with stateful, resumable nodes.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job: return {"status": "error", "message": "Job not found"}

        # 1. Initialize or Resume Workflow
        from app.models.workflow import ApplicationWorkflow, WorkflowStatus
        from app.services.workflow_orchestrator import WorkflowOrchestrator
        workflow = db.query(ApplicationWorkflow).filter(
            ApplicationWorkflow.job_id == job_id,
            ApplicationWorkflow.user_id == user_id,
            ApplicationWorkflow.status.in_([
                WorkflowStatus.PENDING,
                WorkflowStatus.RUNNING,
                WorkflowStatus.PAUSED_FOR_HUMAN,
            ])
        ).first()

        if not workflow:
            workflow = WorkflowOrchestrator.initialize_workflow(db, job, user_id)

        # 2. Execution Loop (Distributed Step Pattern)
        while True:
            step = WorkflowOrchestrator.execute_next_step(db, workflow.id)
            if not step: break # Workflow completed all nodes

            logger.info(f"Executing workflow step: {step.name} (ID: {step.id})")
            
            try:
                # Actual step handlers (to be expanded with Playwright logic)
                if step.name == "NAVIGATE_TO_JOB":
                    # Placeholder for page.goto logic
                    WorkflowOrchestrator.complete_step(db, step.id, {"url": job.url})
                
                elif step.name == "UPLOAD_RESUME":
                    # Placeholder for file upload logic
                    WorkflowOrchestrator.complete_step(db, step.id, {"file_uploaded": True})

                elif step.name == "SUBMIT_APPLICATION":
                    from app.services.state_manager import StateManager
                    WorkflowOrchestrator.pause_step_for_human(
                        db,
                        step.id,
                        "Final submission requires explicit approval before the application is sent.",
                        {
                            "approval_boundary": "final_submit",
                            "resume_upload_preserved": True,
                        },
                    )
                    StateManager.transition_job(
                        db,
                        job,
                        JobStatus.APPLYING_PENDING_APPROVAL,
                        user_id,
                        payload={
                            "job_id": job_id,
                            "workflow_id": workflow.id,
                            "step_id": step.id,
                            "reason": "final_submit_approval_required",
                        },
                    )
                    return {
                        "status": "paused_for_approval",
                        "workflow_id": workflow.id,
                        "step_id": step.id,
                    }
                
                else:
                    # Default success for placeholder steps
                    WorkflowOrchestrator.complete_step(db, step.id)
                    
            except Exception as e:
                logger.error(f"Step {step.name} failed with error: {e}")
                WorkflowOrchestrator.fail_step(db, step.id, str(e))
                # Trigger task-level retry to handle transient failures
                raise self.retry(exc=e, countdown=60)

        # 3. Final State Sync
        from app.services.state_manager import StateManager
        db.refresh(workflow)
        db.refresh(job)

        if workflow.status == WorkflowStatus.PAUSED_FOR_HUMAN:
            return {"status": "paused_for_approval", "workflow_id": workflow.id}

        if workflow.status == WorkflowStatus.FAILED:
            StateManager.transition_job(
                db,
                job,
                JobStatus.FAILED,
                user_id,
                payload={"job_id": job_id, "workflow_id": workflow.id},
            )
            return {"status": "failed", "workflow_id": workflow.id}

        StateManager.transition_job(db, job, JobStatus.APPLIED, user_id)
        
        return {"status": "success", "workflow_id": workflow.id}

    finally:
        db.close()

@celery_app.task(name="app.workers.tasks.process_resume_task")
def process_resume_task(resume_id: int, user_id: int):
    logger.info(f"Processing resume {resume_id}")
    db = SessionLocal()
    
    try:
        from app.models.profile import Resume
        from app.services.resume_service import ResumeService
        
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume or not resume.file_path:
            return {"status": "error", "message": "Resume or file path not found"}

        # Emit Processing Event
        EventService.emit(user_id, EventType.RESUME_PROCESSING, {"resume_id": resume_id, "name": resume.name}, resource_id=str(resume_id))
        resume.extraction_status = "PROCESSING"
        db.commit()

        # 1. Extract text if not already present
        if not resume.content_text:
            resume.content_text = ResumeService.extract_text_from_file(resume.file_path)
            db.commit()

        # 2. Normalize via AI
        normalized_result = asyncio.run(ResumeService.normalize_resume_content(resume.content_text))
        
        # 3. Handle Review Flow
        if normalized_result:
            resume.extraction_data = normalized_result.get("data", {})
            resume.confidence_scores = normalized_result.get("confidence", {})
            resume.extraction_status = "REVIEW_REQUIRED"
            resume.review_status = "NOT_STARTED"
            # Emit Review Required Event
            EventService.emit(user_id, EventType.RESUME_REVIEW_REQUIRED, {"resume_id": resume_id, "name": resume.name}, resource_id=str(resume_id))
        else:
            resume.extraction_status = "FAILED"
            EventService.emit(user_id, EventType.SYSTEM_ALERT, {"message": f"Failed to process resume {resume.name}", "severity": "error"})
            
        db.commit()
        return {"status": "success", "resume_id": resume_id}

    except Exception as e:
        logger.error(f"Failed to process resume {resume_id}: {e}")
        db.rollback()
        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if resume:
            resume.extraction_status = "FAILED"
            db.commit()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
