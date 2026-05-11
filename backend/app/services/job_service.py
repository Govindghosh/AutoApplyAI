from dataclasses import dataclass

from sqlalchemy.orm import Session
from app.automation.scrapers.registry import supported_source_names
from app.models.job import Job, JobStatus
from app.schemas.job import JobCreate
from app.core.logging import logger
from app.services.job_matching_service import JobMatchingService
from app.services.job_quality_service import JobQualityService


@dataclass(frozen=True)
class JobFilters:
    status: JobStatus | str | None = None
    source: str | None = None
    location: str | None = None
    remote_type: str | None = None
    search: str | None = None
    min_score: float | None = None
    max_score: float | None = None
    sort: str = "quality"


class JobService:
    @staticmethod
    def get_jobs(db: Session, skip: int = 0, limit: int = 100):
        return (
            db.query(Job)
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_jobs_for_user(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        filters: JobFilters | None = None,
    ):
        context = JobMatchingService.build_context(db, user_id)
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        matched_jobs = JobMatchingService.filter_jobs(jobs, context)
        matched_jobs = [
            job for job in matched_jobs if JobService._stored_job_quality_ok(job)
        ]
        filters = filters or JobFilters()
        matched_jobs = [
            job for job in matched_jobs if JobService._matches_filters(job, filters)
        ]
        matched_jobs = JobService._sort_jobs(matched_jobs, filters.sort)
        return matched_jobs[skip : skip + limit]

    @staticmethod
    def get_source_summary_for_user(db: Session, user_id: int) -> list[dict]:
        context = JobMatchingService.build_context(db, user_id)
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        matched_jobs = JobMatchingService.filter_jobs(jobs, context)
        matched_jobs = [
            job for job in matched_jobs if JobService._stored_job_quality_ok(job)
        ]

        supported_sources = supported_source_names()
        counts = {source: 0 for source in supported_sources}
        for job in matched_jobs:
            source = job.source or "Unknown"
            counts[source] = counts.get(source, 0) + 1

        supported_set = set(supported_sources)
        ordered_sources = supported_sources + sorted(
            source for source in counts if source not in supported_set
        )
        return [
            {
                "source": source,
                "count": counts.get(source, 0),
                "supported": source in supported_set,
            }
            for source in ordered_sources
        ]

    @staticmethod
    def get_job(db: Session, job_id: int):
        return db.query(Job).filter(Job.id == job_id).first()

    @staticmethod
    def get_job_by_source_id(db: Session, source_id: str):
        return db.query(Job).filter(Job.source_id == source_id).first()

    @staticmethod
    def get_job_by_url(db: Session, url: str):
        return db.query(Job).filter(Job.url == url).first()

    @staticmethod
    def save_jobs(db: Session, jobs_in: list[JobCreate]):
        new_jobs_count = 0
        for job_create in JobService.normalize_jobs(jobs_in):
            # Simple deduplication by source_id
            existing = JobService.get_job_by_source_id(db, job_create.source_id)
            if existing:
                continue
            existing_url = JobService.get_job_by_url(db, job_create.url)
            if existing_url:
                continue

            db_job = Job(**job_create.model_dump())
            db.add(db_job)
            new_jobs_count += 1

        if new_jobs_count > 0:
            db.commit()
            logger.info(f"Saved {new_jobs_count} new jobs to the database")

        return new_jobs_count

    @staticmethod
    def normalize_jobs(jobs_in: list[JobCreate]) -> list[JobCreate]:
        jobs: list[JobCreate] = []
        seen_signatures: set[str] = set()
        for job_in in jobs_in:
            job_create = JobService._coerce_job(job_in)
            if not job_create:
                continue

            job_create = JobQualityService.clean_job(job_create)
            quality = JobQualityService.evaluate(job_create)
            if not quality.accepted:
                logger.debug(
                    f"Skipping low-quality job from {job_create.source}: "
                    f"{job_create.title} ({quality.score}, {quality.reasons})"
                )
                continue

            signature = JobQualityService.signature(job_create)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            jobs.append(job_create)
        return jobs

    @staticmethod
    def _coerce_job(job_in) -> JobCreate | None:
        if isinstance(job_in, JobCreate):
            return job_in

        if not isinstance(job_in, dict):
            logger.warning(f"Skipping unsupported job payload: {type(job_in).__name__}")
            return None

        source = job_in.get("source") or job_in.get("source_name") or "Unknown"
        url = job_in.get("url")
        title = job_in.get("title")
        company = job_in.get("company") or "Unknown"
        source_id = job_in.get("source_id") or job_in.get("id") or url

        if not source_id or not title or not url:
            logger.warning(f"Skipping incomplete job payload from {source}: {job_in}")
            return None

        return JobCreate(
            source_id=f"{source}:{source_id}",
            title=title,
            company=company,
            location=job_in.get("location"),
            description=job_in.get("description"),
            salary=job_in.get("salary") or job_in.get("salary_range"),
            url=url,
            source=source,
            remote_type=job_in.get("remote_type") or job_in.get("remote"),
            raw_data=job_in.get("raw_data") or job_in,
        )

    @staticmethod
    def _diversify_by_source(jobs: list[Job]) -> list[Job]:
        buckets: dict[str, list[Job]] = {}
        for job in jobs:
            buckets.setdefault(job.source or "Unknown", []).append(job)

        diversified: list[Job] = []
        while any(buckets.values()):
            for source in sorted(buckets.keys()):
                if buckets[source]:
                    diversified.append(buckets[source].pop(0))
        return diversified

    @staticmethod
    def _matches_filters(job: Job, filters: JobFilters) -> bool:
        if filters.status and JobService._status_value(
            job.status
        ) != JobService._status_value(filters.status):
            return False

        if filters.source and filters.source.lower() != "all":
            if (job.source or "").lower() != filters.source.lower():
                return False

        if filters.location:
            location_text = (job.location or "").lower()
            if filters.location.lower() not in location_text:
                return False

        if filters.remote_type and filters.remote_type.lower() != "all":
            remote_text = f"{job.remote_type or ''} {job.location or ''}".lower()
            remote_filter = filters.remote_type.lower()
            has_remote = "remote" in remote_text
            has_hybrid = "hybrid" in remote_text
            if remote_filter == "remote" and not has_remote:
                return False
            if remote_filter == "hybrid" and not has_hybrid:
                return False
            if remote_filter == "onsite" and (has_remote or has_hybrid):
                return False
            if remote_filter == "unknown" and (job.remote_type or job.location):
                return False

        if filters.search:
            search_text = filters.search.lower()
            haystack = " ".join(
                str(value or "")
                for value in (
                    job.title,
                    job.company,
                    job.location,
                    job.description,
                    job.salary,
                    job.source,
                    job.remote_type,
                )
            ).lower()
            if search_text not in haystack:
                return False

        score = job.ai_score or 0
        if filters.min_score is not None and score < filters.min_score:
            return False
        if filters.max_score is not None and score > filters.max_score:
            return False

        return True

    @staticmethod
    def _sort_jobs(jobs: list[Job], sort: str | None) -> list[Job]:
        sort_key = (sort or "quality").lower()
        if sort_key == "newest":
            return sorted(
                jobs,
                key=lambda job: JobService._timestamp(job.created_at),
                reverse=True,
            )
        if sort_key == "score":
            return sorted(
                jobs,
                key=lambda job: (
                    job.ai_score or 0,
                    JobService._stored_job_quality_score(job),
                    JobService._timestamp(job.created_at),
                ),
                reverse=True,
            )
        if sort_key == "source":
            return sorted(
                jobs,
                key=lambda job: ((job.source or "").lower(), (job.title or "").lower()),
            )
        if sort_key == "company":
            return sorted(
                jobs,
                key=lambda job: (
                    (job.company or "").lower(),
                    (job.title or "").lower(),
                ),
            )

        ranked_jobs = sorted(
            jobs,
            key=lambda job: (
                JobService._stored_job_quality_score(job),
                JobService._timestamp(job.created_at),
            ),
            reverse=True,
        )
        return JobService._diversify_by_source(ranked_jobs)

    @staticmethod
    def _status_value(status: JobStatus | str) -> str:
        return getattr(status, "value", status)

    @staticmethod
    def _timestamp(value) -> float:
        try:
            return value.timestamp()
        except Exception:
            return 0

    @staticmethod
    def _stored_job_quality_ok(job: Job) -> bool:
        try:
            quality = JobQualityService.evaluate(
                JobCreate(
                    source_id=job.source_id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    description=job.description,
                    salary=job.salary,
                    url=job.url,
                    source=job.source,
                    remote_type=job.remote_type,
                    raw_data=job.raw_data,
                )
            )
            return quality.accepted
        except Exception:
            return False

    @staticmethod
    def _stored_job_quality_score(job: Job) -> int:
        try:
            quality = JobQualityService.evaluate(
                JobCreate(
                    source_id=job.source_id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    description=job.description,
                    salary=job.salary,
                    url=job.url,
                    source=job.source,
                    remote_type=job.remote_type,
                    raw_data=job.raw_data,
                )
            )
            return quality.score
        except Exception:
            return 0
