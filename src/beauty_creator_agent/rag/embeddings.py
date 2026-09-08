from typing import Protocol

import httpx
from pydantic import TypeAdapter

from beauty_creator_agent.core.errors import ExternalServiceError


class EmbeddingProvider(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


class OllamaEmbeddingProvider:
    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/api/embed", json={"model": self.model, "input": texts}
                )
                response.raise_for_status()
                return TypeAdapter(list[list[float]]).validate_python(response.json()["embeddings"])
        except (httpx.HTTPError, KeyError, TypeError) as exc:
            raise ExternalServiceError(f"Ollama embedding failed: {exc}") from exc

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_documents([text])
        return results[0]
