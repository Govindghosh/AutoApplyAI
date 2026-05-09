import anthropic
from app.core.config import settings
from app.core.logging import logger

class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-3-5-sonnet-20240620"

    async def analyze_job(self, job_description: str, resume_text: str):
        prompt = f"""
        Analyze the following job description and compare it with the candidate's resume.
        
        Job Description:
        {job_description}
        
        Resume:
        {resume_text}
        
        Provide the following in JSON format:
        1. match_score (0-100)
        2. key_missing_skills (list)
        3. resume_improvements (list)
        4. interview_talking_points (list)
        """
        
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            # In a real app, you'd parse the JSON from message.content[0].text
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude analysis failed: {str(e)}")
            return None
