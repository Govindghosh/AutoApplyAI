import aiohttp
from app.core.config import settings
from app.core.logging import logger

class N8NClient:
    def __init__(self):
        self.webhook_url = settings.N8N_WEBHOOK_URL

    async def trigger_event(self, event_name: str, payload: dict):
        if not self.webhook_url:
            logger.warning("N8N_WEBHOOK_URL not configured")
            return None

        async with aiohttp.ClientSession() as session:
            try:
                data = {
                    "event": event_name,
                    "payload": payload
                }
                async with session.post(self.webhook_url, json=data) as response:
                    if response.status == 200:
                        logger.info(f"N8N event triggered: {event_name}")
                        return await response.json()
                    else:
                        logger.error(f"N8N webhook failed: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error triggering N8N event: {str(e)}")
                return None
