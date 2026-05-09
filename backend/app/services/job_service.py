from sqlalchemy.orm import Session
from app.models.job import Job
from app.schemas.job import JobCreate
from app.core.logging import logger

class JobService:
    @staticmethod
    def get_jobs(db: Session, skip: int = 0, limit: int = 100):
        return db.query(Job).offset(skip).limit(limit).all()

    @staticmethod
    def get_job(db: Session, job_id: int):
        return db.query(Job).filter(Job.id == job_id).first()

    @staticmethod
    def get_job_by_source_id(db: Session, source_id: str):
        return db.query(Job).filter(Job.source_id == source_id).first()

    @staticmethod
    def save_jobs(db: Session, jobs_in: list[JobCreate]):
        new_jobs_count = 0
        for job_in in jobs_in:
            # Simple deduplication by source_id
            existing = JobService.get_job_by_source_id(db, job_in.source_id)
            if existing:
                continue
            
            db_job = Job(**job_in.model_dump())
            db.add(db_job)
            new_jobs_count += 1
        
        if new_jobs_count > 0:
            db.commit()
            logger.info(f"Saved {new_jobs_count} new jobs to the database")
        
        return new_jobs_count
