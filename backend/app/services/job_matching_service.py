import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.profile import Resume, UserProfile
from app.services.resume_service import ResumeService

_DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "backend": {
        "backend",
        "back end",
        "api",
        "apis",
        "server",
        "fastapi",
        "django",
        "flask",
        "node",
        "express",
        "spring",
        "microservices",
        "postgresql",
        "mysql",
        "redis",
        "database",
        "python",
        "java",
        "golang",
        "go",
        "ruby",
        "rails",
        "php",
        "laravel",
        "scala",
    },
    "frontend": {
        "frontend",
        "front end",
        "react",
        "next.js",
        "nextjs",
        "vue",
        "angular",
        "javascript",
        "typescript",
        "html",
        "css",
        "tailwind",
        "ui engineer",
        "svelte",
        "web developer",
    },
    "fullstack": {
        "fullstack",
        "full stack",
        "frontend",
        "backend",
        "react",
        "node",
        "api",
        "typescript",
        "javascript",
    },
    "data": {
        "data",
        "analytics",
        "analyst",
        "sql",
        "etl",
        "warehouse",
        "tableau",
        "power bi",
        "pandas",
        "spark",
        "python",
        "bi",
        "dbt",
        "airflow",
    },
    "ai": {
        "ai",
        "ml",
        "machine learning",
        "llm",
        "deep learning",
        "nlp",
        "computer vision",
        "openai",
        "gemini",
        "pytorch",
        "tensorflow",
        "rag",
        "generative ai",
    },
    "devops": {
        "devops",
        "sre",
        "platform",
        "cloud",
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "terraform",
        "ci/cd",
        "linux",
        "jenkins",
        "github actions",
        "ansible",
    },
    "qa": {
        "qa",
        "quality",
        "test",
        "automation",
        "selenium",
        "playwright",
        "cypress",
        "manual testing",
        "sdet",
    },
    "mobile": {
        "mobile",
        "android",
        "ios",
        "react native",
        "flutter",
        "swift",
        "kotlin",
    },
    "design": {
        "designer",
        "design",
        "ux",
        "ui",
        "figma",
        "product design",
    },
    "product": {
        "product manager",
        "product owner",
        "product management",
        "roadmap",
        "go-to-market",
        "gtm",
    },
}

_ROLE_HINTS_BY_DOMAIN: dict[str, set[str]] = {
    "backend": {
        "backend engineer",
        "backend developer",
        "software engineer",
        "python developer",
        "api engineer",
    },
    "frontend": {
        "frontend engineer",
        "frontend developer",
        "react developer",
        "ui engineer",
    },
    "fullstack": {"full stack engineer", "fullstack engineer", "full stack developer"},
    "data": {"data analyst", "data engineer", "business analyst", "analytics engineer"},
    "ai": {"ai engineer", "ml engineer", "machine learning engineer", "llm engineer"},
    "devops": {
        "devops engineer",
        "site reliability engineer",
        "platform engineer",
        "cloud engineer",
    },
    "qa": {"qa engineer", "automation tester", "test engineer"},
    "mobile": {"mobile developer", "android developer", "ios developer"},
    "design": {"product designer", "ux designer", "ui designer"},
    "product": {"product manager", "product owner"},
}

_GENERIC_ROLE_WORDS = {
    "engineer",
    "developer",
    "software",
    "remote",
    "senior",
    "junior",
    "lead",
    "staff",
    "principal",
    "intern",
    "manager",
    "specialist",
}

_ROLE_NOUNS = {
    "engineer",
    "developer",
    "architect",
    "manager",
    "analyst",
    "designer",
    "consultant",
    "specialist",
    "lead",
    "administrator",
    "scientist",
    "tester",
}

_PLACEHOLDER_ROLE_PARTS = {"awaiting extraction", "unknown", "not available", "n/a"}


@dataclass(frozen=True)
class JobMatchContext:
    user_id: int
    profile_id: int | None = None
    base_resume_id: int | None = None
    current_title: str = ""
    resume_text: str = ""
    target_roles: set[str] = field(default_factory=set)
    skills: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)
    domain_keywords: set[str] = field(default_factory=set)
    preferred_locations: set[str] = field(default_factory=set)

    @property
    def has_filter_signal(self) -> bool:
        return bool(self.target_roles or self.skills or self.domain_keywords)


class JobMatchingService:
    """
    Lightweight resume/domain gate used before expensive AI analysis.

    AI still performs the detailed match scoring; this service only prevents
    clearly unrelated jobs from entering the user's pipeline.
    """

    MIN_SCORE = 4

    @classmethod
    def build_context(cls, db: Session, user_id: int) -> JobMatchContext:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return JobMatchContext(user_id=user_id)

        base_resume = cls._get_base_resume(db, profile.id)
        extraction_data = cls._dict_value(getattr(base_resume, "extraction_data", None))
        resume_text = (getattr(base_resume, "content_text", None) or "").strip()

        local_resume_data: dict[str, Any] = {}
        if resume_text:
            local_resume_data = ResumeService.normalize_resume_content_locally(
                resume_text
            ).get("data", {})

        current_title = cls._current_title(profile)
        skills = cls._collect_skills(profile, extraction_data, local_resume_data)
        target_roles = cls._collect_target_roles(
            profile, extraction_data, local_resume_data
        )
        if current_title:
            target_roles.add(current_title)
        preferred_locations = cls._collect_preferred_locations(profile)
        domains = cls._derive_domains(target_roles, skills)
        domain_keywords = cls._derive_domain_keywords(domains, target_roles, skills)

        if not resume_text:
            resume_text = cls._profile_resume_text(profile, target_roles, skills)

        return JobMatchContext(
            user_id=user_id,
            profile_id=profile.id,
            base_resume_id=getattr(base_resume, "id", None),
            current_title=current_title,
            resume_text=resume_text,
            target_roles=target_roles,
            skills=skills,
            domains=domains,
            domain_keywords=domain_keywords,
            preferred_locations=preferred_locations,
        )

    @classmethod
    def filter_jobs(cls, jobs: Iterable[Job], context: JobMatchContext) -> list[Job]:
        if not context.has_filter_signal:
            return list(jobs)
        return [job for job in jobs if cls.matches(job, context)]

    @classmethod
    def matches(cls, job: Job, context: JobMatchContext) -> bool:
        if not context.has_filter_signal:
            return True

        explanation = cls.explain_match(job, context)
        return bool(explanation["is_match"])

    @classmethod
    def explain_match(cls, job: Job, context: JobMatchContext) -> dict[str, Any]:
        title = cls._normalize_text(getattr(job, "title", ""))
        body = cls._normalize_text(
            " ".join(
                str(value or "")
                for value in (
                    getattr(job, "title", ""),
                    getattr(job, "company", ""),
                    getattr(job, "location", ""),
                    getattr(job, "description", ""),
                    getattr(job, "source", ""),
                    getattr(job, "remote_type", ""),
                    cls._raw_text(getattr(job, "raw_data", None)),
                )
            )
        )

        matched_roles = cls._phrases_in_text(context.target_roles, body)
        matched_title_roles = cls._phrases_in_text(
            context.target_roles | context.domain_keywords, title
        )
        matched_skills = cls._phrases_in_text(context.skills, body)
        matched_domain_keywords = cls._phrases_in_text(context.domain_keywords, body)

        specific_roles = {
            role
            for role in context.target_roles
            if any(word not in _GENERIC_ROLE_WORDS for word in cls._words(role))
        }
        matched_specific_roles = matched_roles & specific_roles

        score = (
            len(matched_title_roles) * 3
            + len(matched_specific_roles) * 3
            + len(matched_roles) * 2
            + len(matched_skills) * 2
            + len(matched_domain_keywords)
        )

        has_role_or_domain_signal = bool(
            matched_title_roles
            or matched_specific_roles
            or (matched_domain_keywords and not context.target_roles)
        )
        has_skill_signal = len(matched_skills) >= 2 or (
            len(matched_skills) >= 1 and bool(matched_domain_keywords or matched_roles)
        )
        is_match = score >= cls.MIN_SCORE and (
            has_role_or_domain_signal or has_skill_signal
        )

        return {
            "is_match": is_match,
            "score": score,
            "matched_roles": sorted(matched_roles),
            "matched_skills": sorted(matched_skills),
            "matched_domain_keywords": sorted(matched_domain_keywords),
            "domains": sorted(context.domains),
        }

    @classmethod
    def resume_text_for_analysis(cls, context: JobMatchContext) -> str:
        return (
            context.resume_text
            or "Experienced professional with relevant domain skills."
        )

    @classmethod
    def search_query_for_scrapers(cls, context: JobMatchContext) -> str:
        if context.current_title and cls._is_meaningful_role(context.current_title):
            return context.current_title

        specific_roles = [
            role
            for role in sorted(
                context.target_roles,
                key=lambda item: (len(item.split()), len(item)),
                reverse=True,
            )
            if cls._is_meaningful_role(role)
        ]
        if specific_roles:
            return specific_roles[0]

        if context.domains:
            domain = sorted(context.domains)[0]
            hints = sorted(_ROLE_HINTS_BY_DOMAIN.get(domain, []), key=len, reverse=True)
            if hints:
                return hints[0]

        if context.skills:
            return " ".join(sorted(context.skills)[:3])

        return "Software Engineer"

    @staticmethod
    def search_location_for_scrapers(context: JobMatchContext) -> str:
        if context.preferred_locations:
            return sorted(context.preferred_locations)[0]
        return "Remote"

    @staticmethod
    def _get_base_resume(db: Session, profile_id: int) -> Resume | None:
        return (
            db.query(Resume)
            .filter(
                Resume.profile_id == profile_id, Resume.is_base == True
            )  # noqa: E712
            .order_by(Resume.created_at.desc())
            .first()
            or db.query(Resume)
            .filter(Resume.profile_id == profile_id)
            .order_by(Resume.created_at.desc())
            .first()
        )

    @classmethod
    def _collect_skills(
        cls,
        profile: UserProfile,
        extraction_data: dict[str, Any],
        local_resume_data: dict[str, Any],
    ) -> set[str]:
        skills: set[str] = set()
        for source in (
            getattr(profile, "skills", None),
            extraction_data.get("skills"),
            local_resume_data.get("skills"),
            cls._flatten_dict_values(getattr(profile, "tech_stack", None)),
            cls._flatten_dict_values(extraction_data.get("tech_stack")),
            cls._flatten_dict_values(local_resume_data.get("tech_stack")),
        ):
            for value in cls._list_value(source):
                normalized = cls._normalize_phrase(value)
                if normalized:
                    skills.add(normalized)
        return skills

    @classmethod
    def _collect_target_roles(
        cls,
        profile: UserProfile,
        extraction_data: dict[str, Any],
        local_resume_data: dict[str, Any],
    ) -> set[str]:
        roles: set[str] = set()
        for source in (
            getattr(profile, "preferred_roles", None),
            getattr(profile, "title", None),
            extraction_data.get("title"),
            local_resume_data.get("title"),
        ):
            for value in cls._list_value(source):
                normalized = cls._normalize_phrase(value)
                if cls._is_meaningful_role(normalized):
                    roles.add(normalized)
        return roles

    @classmethod
    def _current_title(cls, profile: UserProfile) -> str:
        normalized = cls._normalize_phrase(getattr(profile, "title", None))
        return normalized if cls._is_meaningful_role(normalized) else ""

    @classmethod
    def _collect_preferred_locations(cls, profile: UserProfile) -> set[str]:
        locations: set[str] = set()
        for value in cls._list_value(getattr(profile, "preferred_locations", None)):
            normalized = cls._normalize_phrase(value)
            if normalized:
                locations.add(normalized.title())

        remote_preference = cls._normalize_phrase(
            getattr(profile, "remote_preference", None)
        )
        if "remote" in remote_preference:
            locations.add("Remote")

        return locations

    @classmethod
    def _derive_domains(cls, roles: set[str], skills: set[str]) -> set[str]:
        text = " ".join(sorted(roles | skills))
        domains: set[str] = set()
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            if any(cls._contains_phrase(text, keyword) for keyword in keywords):
                domains.add(domain)
        return domains

    @classmethod
    def _derive_domain_keywords(
        cls,
        domains: set[str],
        target_roles: set[str],
        skills: set[str],
    ) -> set[str]:
        keywords = set(target_roles)
        for domain in domains:
            keywords.update(_DOMAIN_KEYWORDS.get(domain, set()))
            keywords.update(_ROLE_HINTS_BY_DOMAIN.get(domain, set()))
        keywords.update(skill for skill in skills if len(skill) > 1)
        return {
            keyword
            for keyword in (cls._normalize_phrase(value) for value in keywords)
            if keyword
        }

    @staticmethod
    def _profile_resume_text(
        profile: UserProfile, target_roles: set[str], skills: set[str]
    ) -> str:
        parts = [
            getattr(profile, "title", None),
            (
                f"Target roles: {', '.join(sorted(target_roles))}"
                if target_roles
                else None
            ),
            f"Skills: {', '.join(sorted(skills))}" if skills else None,
            (
                f"Experience years: {profile.experience_years}"
                if getattr(profile, "experience_years", None)
                else None
            ),
            getattr(profile, "bio", None),
        ]
        return "\n".join(str(part) for part in parts if part)

    @staticmethod
    def _dict_value(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @classmethod
    def _list_value(cls, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, dict):
            return cls._flatten_dict_values(value)
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    @classmethod
    def _flatten_dict_values(cls, value: Any) -> list[Any]:
        if not isinstance(value, dict):
            return []
        flattened: list[Any] = []
        for item in value.values():
            if isinstance(item, dict):
                flattened.extend(cls._flatten_dict_values(item))
            elif isinstance(item, (list, tuple, set)):
                flattened.extend(item)
            elif item is not None:
                flattened.append(item)
        return flattened

    @classmethod
    def _phrases_in_text(cls, phrases: set[str], text: str) -> set[str]:
        return {phrase for phrase in phrases if cls._contains_phrase(text, phrase)}

    @classmethod
    def _contains_phrase(cls, text: str, phrase: str) -> bool:
        normalized_phrase = cls._normalize_phrase(phrase)
        if not normalized_phrase:
            return False
        return (
            re.search(
                rf"(?<![a-z0-9+#.]){re.escape(normalized_phrase)}(?![a-z0-9+#.])", text
            )
            is not None
        )

    @staticmethod
    def _normalize_phrase(value: Any) -> str:
        text = str(value or "").strip().lower()
        text = text.replace("&", " and ")
        text = re.sub(r"[^a-z0-9+#./\s-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def _normalize_text(cls, value: Any) -> str:
        text = cls._normalize_phrase(value)
        return f" {text} "

    @staticmethod
    def _words(value: str) -> set[str]:
        return set(re.findall(r"[a-z0-9+#.]+", value.lower()))

    @staticmethod
    def _is_meaningful_role(value: str) -> bool:
        if not value or any(part in value for part in _PLACEHOLDER_ROLE_PARTS):
            return False
        words = set(re.findall(r"[a-z0-9+#.]+", value.lower()))
        return bool(words & _ROLE_NOUNS)

    @classmethod
    def _raw_text(cls, raw_data: Any) -> str:
        if isinstance(raw_data, dict):
            return " ".join(
                str(value)
                for value in raw_data.values()
                if not isinstance(value, (dict, list))
            )
        return str(raw_data or "")
