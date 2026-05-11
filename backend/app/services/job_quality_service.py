import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.schemas.job import JobCreate


_BAD_TITLE_PARTS = {
    "recommended jobs",
    "search jobs",
    "job search",
    "find jobs",
    "upload your cv",
    "create job alert",
    "{search_term_string}",
}

_BAD_COMPANIES = {"unknown", "n/a", "not available", "company"}

_LOW_VALUE_DESCRIPTION_PARTS = {
    "upload your cv",
    "create job alert",
    "sign in to browse",
    "download the app",
    "jobs by location",
    "browse jobs",
}


@dataclass(frozen=True)
class JobQualityResult:
    accepted: bool
    score: int
    reasons: list[str] = field(default_factory=list)


class JobQualityService:
    MIN_SCORE = 45

    @classmethod
    def evaluate(cls, job: JobCreate) -> JobQualityResult:
        score = 0
        reasons: list[str] = []

        title = cls._clean(job.title)
        company = cls._clean(job.company)
        description = cls._clean(job.description)
        url = (job.url or "").strip()

        if not title:
            reasons.append("missing_title")
        elif len(title) < 4:
            reasons.append("title_too_short")
        elif any(part in title.lower() for part in _BAD_TITLE_PARTS):
            reasons.append("placeholder_title")
        else:
            score += 25
            if cls._looks_like_real_role(title):
                score += 15

        if company and company.lower() not in _BAD_COMPANIES:
            score += 15
        else:
            reasons.append("weak_company")

        if cls._valid_url(url):
            score += 15
        else:
            reasons.append("invalid_url")

        if description and len(description) >= 80:
            score += 20
        elif description and len(description) >= 30:
            score += 10
        else:
            reasons.append("thin_description")

        if description and any(part in description.lower() for part in _LOW_VALUE_DESCRIPTION_PARTS):
            score -= 15
            reasons.append("portal_chrome_description")

        if job.salary:
            score += 5
        if job.location:
            score += 5
        if job.remote_type:
            score += 5

        score = max(score, 0)
        accepted = score >= cls.MIN_SCORE and not {"missing_title", "placeholder_title", "invalid_url"} & set(reasons)
        return JobQualityResult(accepted=accepted, score=score, reasons=reasons)

    @classmethod
    def clean_job(cls, job: JobCreate) -> JobCreate:
        quality = cls.evaluate(job)
        raw_data: dict[str, Any] = job.raw_data.copy() if isinstance(job.raw_data, dict) else {}
        raw_data["quality"] = {
            "score": quality.score,
            "reasons": quality.reasons,
        }
        return job.model_copy(
            update={
                "title": cls._compact(job.title),
                "company": cls._compact(job.company),
                "location": cls._compact(job.location),
                "description": cls._compact(job.description),
                "salary": cls._compact(job.salary),
                "url": (job.url or "").strip(),
                "raw_data": raw_data,
            }
        )

    @staticmethod
    def signature(job: JobCreate) -> str:
        title = re.sub(r"[^a-z0-9]+", " ", (job.title or "").lower()).strip()
        company = re.sub(r"[^a-z0-9]+", " ", (job.company or "").lower()).strip()
        return f"{title}|{company}"

    @staticmethod
    def _clean(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _compact(value: Any) -> str | None:
        if value is None:
            return None
        text = re.sub(r"\s+", " ", str(value)).strip()
        return text or None

    @staticmethod
    def _valid_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def _looks_like_real_role(title: str) -> bool:
        role_words = {
            "engineer",
            "developer",
            "architect",
            "analyst",
            "manager",
            "designer",
            "scientist",
            "consultant",
            "specialist",
            "administrator",
            "tester",
            "lead",
            "intern",
        }
        words = set(re.findall(r"[a-z0-9+#.]+", title.lower()))
        return bool(words & role_words)
