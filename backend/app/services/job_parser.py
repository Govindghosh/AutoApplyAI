from typing import Dict, Any, Optional
import httpx
from bs4 import BeautifulSoup
from app.core.logging import logger
from app.services.ai_service import AIService
import asyncio

class UniversalJobParser:
    @staticmethod
    async def parse_url(url: str) -> Dict[str, Any]:
        """
        Detects the job platform and extracts structured data.
        """
        if "greenhouse.io" in url:
            return await UniversalJobParser._parse_greenhouse(url)
        if "lever.co" in url:
            return await UniversalJobParser._parse_lever(url)
            
        # Fallback to AI-based generic extraction
        return await UniversalJobParser._parse_generic(url)

    @staticmethod
    async def _parse_greenhouse(url: str) -> Dict[str, Any]:
        logger.info(f"Detected Greenhouse URL: {url}")
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            return {
                "title": soup.find("h1", class_="app-title").text.strip() if soup.find("h1", class_="app-title") else "Unknown Title",
                "company": soup.find("span", class_="company-name").text.strip() if soup.find("span", class_="company-name") else "Unknown Company",
                "description": soup.find("div", id="content").text.strip() if soup.find("div", id="content") else "",
                "source_type": "greenhouse"
            }

    @staticmethod
    async def _parse_lever(url: str) -> Dict[str, Any]:
        logger.info(f"Detected Lever URL: {url}")
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            return {
                "title": soup.find("h2").text.strip() if soup.find("h2") else "Unknown Title",
                "company": "Lever Client", # Lever often doesn't have company name in simple tags
                "description": soup.find("div", class_="content").text.strip() if soup.find("div", class_="content") else "",
                "source_type": "lever"
            }

    @staticmethod
    async def _parse_generic(url: str) -> Dict[str, Any]:
        """
        Uses AI to extract structured job data from any random website.
        """
        logger.info(f"Using Generic AI parser for: {url}")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=30.0)
                html_snippet = resp.text[:10000] # Limit size for AI
                
                ai_service = AIService()
                prompt = f"""
                Extract the Job Title, Company Name, and Job Description from this HTML snippet.
                HTML:
                {html_snippet}
                
                Return JSON format: {{"title": "...", "company": "...", "description": "..."}}
                """
                
                return await ai_service.generate_json(
                    prompt,
                    task="job_parsing",
                    max_tokens=2000,
                )
        except Exception as e:
            logger.error(f"Generic AI parsing failed: {e}")
            return {"title": "Unknown", "company": "Unknown", "description": ""}
