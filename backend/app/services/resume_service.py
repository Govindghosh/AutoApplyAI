import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any
from pypdf import PdfReader
from sqlalchemy.orm import Session
from app.models.profile import Resume, UserProfile
from app.services.ai_service import AIService
from app.core.logging import logger

class ResumeService:
    @staticmethod
    def extract_text_from_pdf(file_content: bytes) -> str:
        try:
            reader = PdfReader(io.BytesIO(file_content))
            text = ""
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {e}")
            raise e

    @staticmethod
    def extract_text_from_docx(file_content: bytes) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(file_content)) as docx:
                xml_content = docx.read("word/document.xml")
            root = ET.fromstring(xml_content)
            namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            return "\n".join(node.text for node in root.findall(".//w:t", namespace) if node.text)
        except Exception as e:
            logger.error(f"Failed to extract text from DOCX: {e}")
            raise e

    @staticmethod
    def extract_text_from_doc(file_content: bytes) -> str:
        return file_content.decode("utf-8", errors="ignore")

    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        path = Path(file_path)
        file_content = path.read_bytes()
        ext = path.suffix.lower()

        if ext == ".pdf":
            return ResumeService.extract_text_from_pdf(file_content)
        if ext == ".docx":
            return ResumeService.extract_text_from_docx(file_content)
        if ext == ".doc":
            return ResumeService.extract_text_from_doc(file_content)

        raise ValueError(f"Unsupported resume file type: {ext}")

    @staticmethod
    async def normalize_resume_content(text: str) -> Dict[str, Any]:
        """
        Uses AI to convert raw resume text into canonical structured data.
        """
        ai_service = AIService()
        prompt = (
            "Extract the following information from this resume text into a clean JSON object.\n\n"
            f"RESUME TEXT:\n{text}\n\n"
            "Required Fields:\n"
            "- full_name\n"
            "- title\n"
            "- experience_years (integer)\n"
            "- skills (list of strings)\n"
            "- tech_stack (dict with categories like 'backend', 'frontend', 'database', etc.)\n"
            "- companies (list of strings)\n\n"
            "Also, for each field, provide a confidence score between 0.0 and 1.0.\n\n"
            'Return ONLY valid JSON in this exact format:\n'
            '{"data": {"full_name": "...", "title": "...", "experience_years": 0, "skills": [], "tech_stack": {}, "companies": []}, '
            '"confidence": {"full_name": 0.99, "skills": 0.85}}'
        )
        
        try:
            result = await ai_service.generate_json(
                prompt,
                task="resume_normalization",
                max_tokens=2500,
            )
            if result.get("data"):
                return ResumeService._normalize_result_shape(result)
        except Exception as e:
            logger.warning(f"Resume normalization failed, using local parser fallback: {e}")

        return ResumeService.normalize_resume_content_locally(text)

    @staticmethod
    def _parse_ai_json_response(text: str) -> Dict[str, Any]:
        clean_text = (text or "").strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?", "", clean_text).strip()
            clean_text = re.sub(r"```$", "", clean_text).strip()
        return json.loads(clean_text)

    @staticmethod
    def _normalize_result_shape(result: Dict[str, Any]) -> Dict[str, Any]:
        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        confidence = result.get("confidence") if isinstance(result.get("confidence"), dict) else {}
        return {"data": data, "confidence": confidence}

    @staticmethod
    def normalize_resume_content_locally(text: str) -> Dict[str, Any]:
        clean_text = re.sub(r"\r\n?", "\n", text or "").strip()
        lines = [line.strip() for line in clean_text.split("\n") if line.strip()]

        full_name = ResumeService._extract_name(lines)
        title = ResumeService._extract_title(lines)
        experience_years = ResumeService._extract_experience_years(clean_text)
        skills = ResumeService._extract_skills(clean_text)
        tech_stack = ResumeService._build_tech_stack(skills)
        companies = ResumeService._extract_companies(lines)

        data = {
            "full_name": full_name,
            "title": title,
            "experience_years": experience_years,
            "skills": skills,
            "tech_stack": tech_stack,
            "companies": companies,
        }
        confidence = {
            "full_name": 0.65 if full_name else 0.1,
            "title": 0.55 if title else 0.1,
            "experience_years": 0.7 if experience_years else 0.2,
            "skills": 0.75 if skills else 0.2,
            "tech_stack": 0.7 if tech_stack else 0.2,
            "companies": 0.45 if companies else 0.1,
        }
        return {"data": data, "confidence": confidence}

    @staticmethod
    def _extract_name(lines: list[str]) -> str:
        for line in lines[:8]:
            if "@" in line or re.search(r"\d{6,}", line):
                continue
            words = re.findall(r"[A-Za-z]+", line)
            if 2 <= len(words) <= 4 and len(line) <= 60:
                return " ".join(word.capitalize() for word in words)
        return ""

    @staticmethod
    def _extract_title(lines: list[str]) -> str:
        title_keywords = (
            "engineer", "developer", "architect", "manager", "analyst", "designer",
            "consultant", "specialist", "lead", "intern", "administrator", "scientist",
        )
        for line in lines[:15]:
            lowered = line.lower()
            if any(keyword in lowered for keyword in title_keywords) and len(line) <= 90:
                return line
        return ""

    @staticmethod
    def _extract_experience_years(text: str) -> int:
        patterns = [
            r"(\d+)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience",
            r"experience\s*(?:of)?\s*(\d+)\+?\s*(?:years|yrs)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0

    @staticmethod
    def _extract_skills(text: str) -> list[str]:
        known_skills = [
            "Python", "FastAPI", "Django", "Flask", "JavaScript", "TypeScript", "React",
            "Next.js", "Node.js", "Express", "PostgreSQL", "MySQL", "MongoDB", "Redis",
            "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "CI/CD",
            "SQL", "NoSQL", "REST", "GraphQL", "Celery", "RabbitMQ", "Kafka", "Linux",
            "HTML", "CSS", "Tailwind", "Java", "Spring", "C++", "C#", ".NET",
            "Machine Learning", "LLM", "OpenAI", "Gemini", "Playwright", "Selenium",
        ]
        found = []
        lowered = text.lower()
        for skill in known_skills:
            pattern = re.escape(skill.lower()).replace("\\ ", r"\s+")
            if re.search(rf"(?<![a-z0-9+#.]){pattern}(?![a-z0-9+#.])", lowered):
                found.append(skill)
        return found

    @staticmethod
    def _build_tech_stack(skills: list[str]) -> Dict[str, list[str]]:
        categories = {
            "backend": {"Python", "FastAPI", "Django", "Flask", "Node.js", "Express", "Java", "Spring", "C#", ".NET"},
            "frontend": {"JavaScript", "TypeScript", "React", "Next.js", "HTML", "CSS", "Tailwind"},
            "database": {"PostgreSQL", "MySQL", "MongoDB", "Redis", "SQL", "NoSQL"},
            "devops": {"Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "CI/CD", "Linux"},
            "automation": {"Playwright", "Selenium", "Celery", "RabbitMQ", "Kafka"},
            "ai": {"Machine Learning", "LLM", "OpenAI", "Gemini"},
        }
        return {
            category: [skill for skill in skills if skill in category_skills]
            for category, category_skills in categories.items()
            if any(skill in category_skills for skill in skills)
        }

    @staticmethod
    def _extract_companies(lines: list[str]) -> list[str]:
        companies = []
        company_markers = ("pvt", "ltd", "inc", "llc", "technologies", "solutions", "systems", "labs")
        for line in lines:
            lowered = line.lower()
            if any(marker in lowered for marker in company_markers) and len(line) <= 100:
                companies.append(line)
        return companies[:8]

    @staticmethod
    def sync_profile_from_resume(db: Session, profile_id: int, normalized_data: Dict[str, Any]):
        """
        Updates the UserProfile with data extracted from the resume.
        """
        profile = db.query(UserProfile).filter(UserProfile.id == profile_id).first()
        if not profile:
            return
            
        # Update fields if they are currently empty or we want to overwrite
        if normalized_data.get("full_name"):
            profile.full_name = normalized_data["full_name"]
        if normalized_data.get("title"):
            profile.title = normalized_data["title"]
        if normalized_data.get("experience_years"):
            profile.experience_years = normalized_data["experience_years"]
        if normalized_data.get("skills"):
            profile.skills = normalized_data["skills"]
        if normalized_data.get("tech_stack"):
            profile.tech_stack = normalized_data["tech_stack"]
            
        db.add(profile)
        db.commit()
        logger.info(f"Profile {profile_id} synced from resume data")
