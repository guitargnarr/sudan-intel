"""Ollama HTTP client wrapper."""

import logging

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.fallback_model = settings.OLLAMA_FALLBACK_MODEL
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(self, prompt: str, model: str = None, temperature: float = 0.3) -> str:
        target_model = model or self.model
        url = f"{self.base_url}/api/generate"

        try:
            resp = await self.client.post(url, json={
                "model": target_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 2000,
                },
            })
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

        except httpx.HTTPStatusError as e:
            if target_model != self.fallback_model:
                logger.warning(
                    "Model %s failed (HTTP %s), falling back to %s",
                    target_model, e.response.status_code, self.fallback_model,
                )
                return await self.generate(prompt, model=self.fallback_model, temperature=temperature)
            raise

        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            return "[Ollama unavailable -- synthesis could not be generated]"

    async def is_available(self) -> bool:
        try:
            resp = await self.client.get(f"{self.base_url}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()
