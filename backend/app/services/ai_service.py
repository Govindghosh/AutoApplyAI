import json
import re
from typing import Any, Callable, Literal, TypeVar

import google.generativeai as genai
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import SecretStr

from app.core.config import settings
from app.core.logging import logger
from app.schemas.job import AIAnalysisOutput

AITask = Literal[
    "job_analysis",
    "resume_normalization",
    "job_parsing",
    "resume_optimization",
    "general",
]
AIProvider = Literal["openai", "anthropic", "gemini", "openrouter"]
ResponseFormat = Literal["text", "json"]
T = TypeVar("T")


DEFAULT_MODELS: dict[AIProvider, str] = {
    "openai": "gpt-5.4-mini",
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.5-flash",
    "openrouter": "openai/gpt-5.4-mini",
}

JOB_ANALYSIS_TOKEN_BUDGET = 1200
MAX_MISSING_KEYWORDS = 8

LOCAL_ANALYSIS_STOPWORDS = {
    "about",
    "above",
    "across",
    "after",
    "again",
    "against",
    "all",
    "also",
    "an",
    "and",
    "any",
    "applicant",
    "application",
    "apply",
    "are",
    "as",
    "at",
    "available",
    "because",
    "been",
    "before",
    "being",
    "best",
    "between",
    "both",
    "but",
    "by",
    "can",
    "candidate",
    "candidates",
    "client",
    "clients",
    "company",
    "could",
    "day",
    "days",
    "developer",
    "during",
    "engineer",
    "etc",
    "every",
    "experience",
    "for",
    "from",
    "full",
    "good",
    "have",
    "hour",
    "hours",
    "hybrid",
    "in",
    "including",
    "into",
    "is",
    "it",
    "job",
    "looking",
    "minimum",
    "month",
    "monthly",
    "months",
    "more",
    "must",
    "need",
    "needed",
    "office",
    "on",
    "onsite",
    "or",
    "other",
    "our",
    "per",
    "preferred",
    "remote",
    "required",
    "requirements",
    "responsibilities",
    "role",
    "salary",
    "senior",
    "software",
    "strong",
    "team",
    "that",
    "the",
    "their",
    "this",
    "time",
    "to",
    "using",
    "we",
    "week",
    "weekly",
    "weeks",
    "with",
    "will",
    "work",
    "working",
    "year",
    "years",
    "you",
    "your",
}

LOCAL_ANALYSIS_TECH_TERMS = {
    "ai",
    "api",
    "aws",
    "azure",
    "celery",
    "css",
    "django",
    "docker",
    "fastapi",
    "flask",
    "gcp",
    "graphql",
    "html",
    "java",
    "javascript",
    "kafka",
    "kubernetes",
    "mongodb",
    "mysql",
    "next.js",
    "node",
    "node.js",
    "postgres",
    "postgresql",
    "python",
    "react",
    "redis",
    "rest",
    "sql",
    "typescript",
}

LOCAL_ANALYSIS_DOMAIN_TERMS = {
    "accessibility",
    "analytics",
    "architecture",
    "automation",
    "backend",
    "caching",
    "cloud",
    "compliance",
    "database",
    "devops",
    "distributed",
    "etl",
    "frontend",
    "infrastructure",
    "integration",
    "microservices",
    "observability",
    "payments",
    "performance",
    "queues",
    "scalability",
    "security",
    "testing",
    "telemetry",
}


TASK_PROVIDER_ORDER: dict[AITask, tuple[AIProvider, ...]] = {
    # Strong structured reasoning first, with writing-oriented and long-context fallbacks.
    "job_analysis": ("openai", "anthropic", "gemini", "openrouter"),
    # Resume text can be long/noisy; Gemini Flash is a good first pass for extraction.
    "resume_normalization": ("gemini", "openai", "anthropic", "openrouter"),
    # HTML snippets are long and messy, so prefer long-context/cost-efficient providers.
    "job_parsing": ("gemini", "openai", "openrouter", "anthropic"),
    # Resume rewriting benefits from Claude-style prose editing, then structured reasoning.
    "resume_optimization": ("anthropic", "openai", "gemini", "openrouter"),
    "general": ("openai", "anthropic", "gemini", "openrouter"),
}


class AIService:
    def __init__(self):
        self.last_provider_name: str | None = None
        self.last_model_name: str | None = None

    @property
    def last_model_descriptor(self) -> str | None:
        if not self.last_provider_name or not self.last_model_name:
            return None
        return f"{self.last_provider_name}:{self.last_model_name}"

    async def analyze_job(
        self, job_title: str, job_description: str, resume_text: str
    ) -> AIAnalysisOutput:
        prompt = f"""
        You are an expert technical recruiter. Analyze the following job description against the provided resume.

        JOB TITLE: {job_title}
        JOB DESCRIPTION:
        {job_description}

        RESUME:
        {resume_text}

        Your output must be a strict JSON object with the following fields:
        - match_score: float between 0 and 100
        - skills_match: float between 0 and 100
        - experience_match: float between 0 and 100
        - location_match: float between 0 and 100
        - tech_stack_match: float between 0 and 100
        - missing_keywords: list of important missing technical skills, tools, frameworks, certifications, or domain competencies only
        - resume_improvements: list of concrete resume changes tied to real missing skills or evidence gaps
        - risk_level: one of "low", "medium", or "high"
        - justification: short string summarizing why

        Do not include generic words, dates, durations, salary terms, locations, availability terms,
        or job-posting filler in missing_keywords. Bad examples: month, months, year, years,
        candidate, company, remote, salary.

        Return ONLY the JSON object.
        """

        try:
            data = await self.generate_json(
                prompt, task="job_analysis", max_tokens=JOB_ANALYSIS_TOKEN_BUDGET
            )
            return self._sanitize_analysis_output(AIAnalysisOutput(**data))
        except Exception as exc:
            logger.warning(
                "AI job analysis failed for '%s'; using local deterministic fallback: %s",
                job_title,
                exc,
            )
            return self._local_job_analysis(job_title, job_description, resume_text)

    async def generate_json(
        self,
        prompt: str,
        task: AITask = "general",
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        return await self._generate_with_fallback(
            prompt=prompt,
            task=task,
            response_format="json",
            max_tokens=max_tokens,
            parser=self._parse_json_response,
        )

    async def generate_text(
        self,
        prompt: str,
        task: AITask = "general",
        max_tokens: int = 2500,
    ) -> str:
        return await self._generate_with_fallback(
            prompt=prompt,
            task=task,
            response_format="text",
            max_tokens=max_tokens,
            parser=lambda text: text.strip(),
        )

    async def _generate_with_fallback(
        self,
        prompt: str,
        task: AITask,
        response_format: ResponseFormat,
        max_tokens: int,
        parser: Callable[[str], T],
    ) -> T:
        providers = self._ordered_configured_providers(task)
        if not providers:
            raise RuntimeError(
                "No AI providers are configured. Add at least one API key in backend/.env."
            )

        errors: list[str] = []
        for provider in providers:
            model = self._model_for(provider)
            try:
                text = await self._call_provider(
                    provider=provider,
                    prompt=prompt,
                    response_format=response_format,
                    max_tokens=max_tokens,
                )
                if not text.strip():
                    raise ValueError("empty AI response")

                parsed = parser(text)
                self.last_provider_name = provider
                self.last_model_name = model
                return parsed
            except Exception as exc:
                if self._should_retry_with_lower_token_budget(exc, max_tokens):
                    retry_tokens = max(600, min(max_tokens - 1, max_tokens // 2))
                    try:
                        text = await self._call_provider(
                            provider=provider,
                            prompt=prompt,
                            response_format=response_format,
                            max_tokens=retry_tokens,
                        )
                        if not text.strip():
                            raise ValueError("empty AI response")

                        parsed = parser(text)
                        self.last_provider_name = provider
                        self.last_model_name = model
                        return parsed
                    except Exception as retry_exc:
                        errors.append(
                            f"{provider}:{model} retry with {retry_tokens} tokens failed: {retry_exc}"
                        )

                message = f"{provider}:{model} failed: {exc}"
                errors.append(message)
                logger.warning(message)

        raise RuntimeError("All configured AI providers failed. " + " | ".join(errors))

    async def _call_provider(
        self,
        provider: AIProvider,
        prompt: str,
        response_format: ResponseFormat,
        max_tokens: int,
    ) -> str:
        if provider == "openai":
            return await self._call_openai(prompt, response_format, max_tokens)
        if provider == "anthropic":
            return await self._call_anthropic(prompt, response_format, max_tokens)
        if provider == "gemini":
            return await self._call_gemini(prompt, response_format)
        if provider == "openrouter":
            return await self._call_openrouter(prompt, response_format, max_tokens)
        raise ValueError(f"Unknown AI provider: {provider}")

    async def _call_openai(
        self,
        prompt: str,
        response_format: ResponseFormat,
        max_tokens: int,
    ) -> str:
        client = AsyncOpenAI(api_key=self._api_key_for("openai"))
        kwargs: dict[str, Any] = {
            "model": self._model_for("openai"),
            "messages": self._messages(prompt, response_format),
            "max_completion_tokens": max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def _call_openrouter(
        self,
        prompt: str,
        response_format: ResponseFormat,
        max_tokens: int,
    ) -> str:
        client = AsyncOpenAI(
            api_key=self._api_key_for("openrouter"),
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://autoapplyai.local",
                "X-Title": settings.PROJECT_NAME,
            },
        )
        kwargs: dict[str, Any] = {
            "model": self._model_for("openrouter"),
            "messages": self._messages(prompt, response_format),
            "max_tokens": max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def _call_anthropic(
        self,
        prompt: str,
        response_format: ResponseFormat,
        max_tokens: int,
    ) -> str:
        client = AsyncAnthropic(api_key=self._api_key_for("anthropic"))
        system = self._system_prompt(response_format)
        message = await client.messages.create(
            model=self._model_for("anthropic"),
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "\n".join(
            block.text
            for block in message.content
            if getattr(block, "type", None) == "text"
        )

    async def _call_gemini(self, prompt: str, response_format: ResponseFormat) -> str:
        genai.configure(api_key=self._api_key_for("gemini"))
        model = genai.GenerativeModel(self._model_for("gemini"))
        kwargs: dict[str, Any] = {}
        if response_format == "json":
            kwargs["generation_config"] = {"response_mime_type": "application/json"}

        response = await model.generate_content_async(prompt, **kwargs)
        return response.text or ""

    def _ordered_configured_providers(self, task: AITask) -> list[AIProvider]:
        return [
            provider
            for provider in TASK_PROVIDER_ORDER.get(
                task, TASK_PROVIDER_ORDER["general"]
            )
            if self._api_key_for(provider)
        ]

    def _api_key_for(self, provider: AIProvider) -> str:
        setting_by_provider = {
            "openai": settings.OPENAI_API_KEY,
            "anthropic": settings.ANTHROPIC_API_KEY,
            "gemini": settings.GEMINI_API_KEY,
            "openrouter": settings.OPENROUTER_API_KEY,
        }
        value = setting_by_provider[provider]
        if isinstance(value, SecretStr):
            return value.get_secret_value().strip()
        return str(value or "").strip()

    def _model_for(self, provider: AIProvider) -> str:
        setting_by_provider = {
            "openai": settings.OPENAI_MODEL,
            "anthropic": settings.ANTHROPIC_MODEL,
            "gemini": settings.GEMINI_MODEL,
            "openrouter": settings.OPENROUTER_MODEL,
        }
        configured = str(setting_by_provider[provider] or "").strip()
        return configured or DEFAULT_MODELS[provider]

    def _messages(
        self, prompt: str, response_format: ResponseFormat
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self._system_prompt(response_format)},
            {"role": "user", "content": prompt},
        ]

    def _system_prompt(self, response_format: ResponseFormat) -> str:
        if response_format == "json":
            return "You are a precise backend AI worker. Return only valid JSON, with no markdown or commentary."
        return "You are a precise backend AI worker. Follow the user request directly."

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        clean_text = (text or "").strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?", "", clean_text).strip()
            clean_text = re.sub(r"```$", "", clean_text).strip()

        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", clean_text, flags=re.DOTALL)
            if not match:
                raise
            data = json.loads(match.group(0))

        if not isinstance(data, dict):
            raise ValueError("AI JSON response must be an object")
        return data

    def _local_job_analysis(
        self, job_title: str, job_description: str, resume_text: str
    ) -> AIAnalysisOutput:
        job_terms = self._keyword_terms(f"{job_title} {job_description}")
        resume_terms = self._keyword_terms(resume_text)
        title_terms = self._keyword_terms(job_title)

        matched_terms = job_terms & resume_terms
        missing_terms = sorted(
            (
                term
                for term in job_terms - resume_terms
                if self._is_actionable_missing_keyword(term)
            ),
            key=lambda term: (-len(term), term),
        )[:MAX_MISSING_KEYWORDS]

        skills_match = self._ratio_score(len(matched_terms), len(job_terms))
        title_match = self._ratio_score(
            len(title_terms & resume_terms), len(title_terms)
        )
        tech_stack_match = self._tech_stack_score(job_terms, resume_terms)
        experience_match = 65.0 if matched_terms else 35.0
        location_match = (
            85.0 if "remote" in f"{job_title} {job_description}".lower() else 70.0
        )

        match_score = round(
            skills_match * 0.35
            + title_match * 0.2
            + tech_stack_match * 0.25
            + experience_match * 0.1
            + location_match * 0.1,
            2,
        )

        risk_level = (
            "low" if match_score >= 75 else "medium" if match_score >= 55 else "high"
        )
        improvements = self._resume_improvements_for_missing_terms(missing_terms)

        self.last_provider_name = "local"
        self.last_model_name = "deterministic-match"

        return self._sanitize_analysis_output(
            AIAnalysisOutput(
                match_score=match_score,
                skills_match=skills_match,
                experience_match=experience_match,
                location_match=location_match,
                tech_stack_match=tech_stack_match,
                missing_keywords=missing_terms,
                resume_improvements=improvements,
                risk_level=risk_level,
                justification=(
                    "Local fallback used because configured AI providers were unavailable or out of quota. "
                    f"Matched {len(matched_terms)} of {len(job_terms)} extracted job keywords."
                ),
            )
        )

    @staticmethod
    def _keyword_terms(text: str) -> set[str]:
        terms = {
            term.lower()
            for term in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{2,}", text or "")
            if term.lower() not in LOCAL_ANALYSIS_STOPWORDS
        }
        return terms

    def _sanitize_analysis_output(
        self, analysis: AIAnalysisOutput
    ) -> AIAnalysisOutput:
        cleaned_missing_keywords = self._clean_missing_keywords(
            analysis.missing_keywords
        )
        removed_keywords = {
            self._normalize_keyword(keyword)
            for keyword in analysis.missing_keywords
        } - {self._normalize_keyword(keyword) for keyword in cleaned_missing_keywords}

        cleaned_improvements = [
            improvement.strip()
            for improvement in analysis.resume_improvements
            if improvement
            and not self._mentions_any_keyword(improvement, removed_keywords)
        ]

        if not cleaned_improvements:
            cleaned_improvements = self._resume_improvements_for_missing_terms(
                cleaned_missing_keywords
            )

        return analysis.model_copy(
            update={
                "missing_keywords": cleaned_missing_keywords,
                "resume_improvements": cleaned_improvements[:5],
            }
        )

    def _clean_missing_keywords(self, keywords: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for keyword in keywords:
            display_keyword = re.sub(r"\s+", " ", str(keyword or "")).strip(" .,:;-")
            normalized = self._normalize_keyword(display_keyword)
            if not normalized or normalized in seen:
                continue
            if not self._is_actionable_missing_keyword(normalized):
                continue

            cleaned.append(display_keyword)
            seen.add(normalized)

            if len(cleaned) >= MAX_MISSING_KEYWORDS:
                break

        return cleaned

    @staticmethod
    def _normalize_keyword(keyword: str) -> str:
        return re.sub(r"\s+", " ", str(keyword or "").strip().lower())

    @staticmethod
    def _mentions_any_keyword(text: str, keywords: set[str]) -> bool:
        normalized_text = AIService._normalize_keyword(text)
        return any(
            re.search(rf"\b{re.escape(keyword)}\b", normalized_text)
            for keyword in keywords
            if keyword
        )

    @staticmethod
    def _resume_improvements_for_missing_terms(terms: list[str]) -> list[str]:
        return [
            f"Add concrete project or impact evidence for {term} if you have relevant experience."
            for term in terms[:3]
        ] or ["Strengthen role-specific impact bullets with measurable outcomes."]

    @staticmethod
    def _is_actionable_missing_keyword(term: str) -> bool:
        normalized = AIService._normalize_keyword(term)
        if not normalized:
            return False

        tokens = re.findall(r"[a-z][a-z0-9+#.]*", normalized)
        if not tokens:
            return False
        if all(token in LOCAL_ANALYSIS_STOPWORDS for token in tokens):
            return False
        if any(token.isdigit() for token in tokens):
            return False
        if any(token in LOCAL_ANALYSIS_STOPWORDS for token in tokens):
            return False

        compact = normalized.replace(" ", "")
        if compact in LOCAL_ANALYSIS_TECH_TERMS:
            return True
        if any(token in LOCAL_ANALYSIS_TECH_TERMS for token in tokens):
            return True
        if any(token in LOCAL_ANALYSIS_DOMAIN_TERMS for token in tokens):
            return True
        if any(symbol in normalized for symbol in ("+", "#", ".")):
            return True

        return len(normalized) >= 4

    @staticmethod
    def _ratio_score(matched: int, total: int) -> float:
        if total <= 0:
            return 50.0
        return round(min(100.0, (matched / total) * 100), 2)

    @staticmethod
    def _tech_stack_score(job_terms: set[str], resume_terms: set[str]) -> float:
        job_tech = job_terms & LOCAL_ANALYSIS_TECH_TERMS
        if not job_tech:
            return 55.0
        return AIService._ratio_score(len(job_tech & resume_terms), len(job_tech))

    @staticmethod
    def _should_retry_with_lower_token_budget(exc: Exception, max_tokens: int) -> bool:
        if max_tokens <= 700:
            return False
        message = str(exc).lower()
        return (
            "fewer max_tokens" in message
            or "can only afford" in message
            or "requires more credits" in message
        )
