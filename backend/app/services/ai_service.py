import json
from typing import Optional
import google.generativeai as genai
from app.core.config import settings
from app.schemas.job import AIAnalysisOutput
from app.core.logging import logger

class AIService:
    def __init__(self):
        # We'll use Gemini as the primary model for enrichment
        genai.configure(api_key=settings.GEMINI_API_KEY.get_secret_value())
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def analyze_job(self, job_title: str, job_description: str, resume_text: str) -> Optional[AIAnalysisOutput]:
        prompt = f"""
        You are an expert technical recruiter. Analyze the following job description against the provided resume.
        
        JOB TITLE: {job_title}
        JOB DESCRIPTION:
        {job_description}
        
        RESUME:
        {resume_text}
        
        Your output must be a strict JSON object with the following fields:
        - match_score: (float between 0 and 100)
        - skills_match: (float between 0 and 100)
        - experience_match: (float between 0 and 100)
        - location_match: (float between 0 and 100)
        - tech_stack_match: (float between 0 and 100)
        - missing_keywords: (list of strings)
        - resume_improvements: (list of strings)
        - risk_level: (string: "low", "medium", or "high")
        - justification: (string summarizing why)
        
        Return ONLY the JSON object.
        """
        
        try:
            # We use generation_config for structured output if supported, 
            # or just parse the text. For Gemini, we can enforce JSON.
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            if not response.text:
                logger.error("AI returned empty response")
                return None
                
            data = json.loads(response.text)
            return AIAnalysisOutput(**data)
            
        except Exception as e:
            logger.error(f"AI Analysis failed: {e}")
            return None
