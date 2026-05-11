from __future__ import annotations

from dataclasses import dataclass
from threading import Thread
from typing import Any

import requests

from app.core.config import settings
from app.core.logging import logger


@dataclass(frozen=True)
class N8NDeliveryResult:
    configured: bool
    delivered: bool
    status_code: int | None = None
    response: Any = None
    error: str | None = None


class N8NClient:
    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = (
            webhook_url if webhook_url is not None else settings.N8N_WEBHOOK_URL
        ).strip()
        self.timeout_seconds = settings.N8N_WEBHOOK_TIMEOUT_SECONDS

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def trigger_event(
        self, event_name: str, payload: dict[str, Any]
    ) -> N8NDeliveryResult:
        if not self.webhook_url:
            logger.debug("N8N_WEBHOOK_URL not configured; skipping n8n delivery")
            return N8NDeliveryResult(configured=False, delivered=False)

        body = {
            "event": event_name,
            "payload": payload,
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=body,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            logger.info("N8N event delivered: %s", event_name)
            return N8NDeliveryResult(
                configured=True,
                delivered=True,
                status_code=response.status_code,
                response=self._safe_response_json(response),
            )
        except Exception as exc:
            logger.warning("N8N webhook delivery failed for %s: %s", event_name, exc)
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            return N8NDeliveryResult(
                configured=True,
                delivered=False,
                status_code=status_code,
                error=str(exc),
            )

    def trigger_event_background(
        self, event_name: str, payload: dict[str, Any]
    ) -> None:
        if not self.webhook_url:
            return

        Thread(
            target=self.trigger_event,
            args=(event_name, payload),
            daemon=True,
            name=f"n8n-{event_name.lower()}",
        ).start()

    @staticmethod
    def _safe_response_json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text
