from app.ai.claude_service import ClaudeService
from app.core.logging import logger

class ResumeOptimizer:
    def __init__(self):
        self.ai_service = ClaudeService()

    async def optimize(self, original_resume: str, job_description: str):
        prompt = f"""
        Optimize the following resume to better match the provided job description.
        Focus on:
        - Quantifying achievements
        - Using relevant keywords from the JD
        - Improving the professional summary
        
        Original Resume:
        {original_resume}
        
        Job Description:
        {job_description}
        
        Return the optimized resume content in a structured format.
        """
        
        try:
            optimized_content = await self.ai_service.analyze_job(job_description, original_resume)
            return optimized_content
        except Exception as e:
            logger.error(f"Resume optimization failed: {str(e)}")
            return original_resume
