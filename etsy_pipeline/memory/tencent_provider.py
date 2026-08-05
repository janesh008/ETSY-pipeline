"""TencentDB MemoryCore HTTP provider implementation and Mock provider for testing.

Communicates with MemoryCore Gateway REST API over HTTP with non-blocking circuit fallback.
"""

from __future__ import annotations

import time
from typing import Any

from etsy_pipeline.memory.base import (
    BaseMemoryProvider,
    MemoryCategory,
    MemoryEntry,
)
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


class TencentDBMemoryProvider(BaseMemoryProvider):
    """Concrete MemoryProvider communicating with TencentDB MemoryCore Gateway over HTTP."""

    def __init__(
        self,
        gateway_url: str = "http://127.0.0.1:8420",
        api_key: str = "",
        namespace: str = "craftdesk-dev",
        timeout_sec: float = 1.5,
        cooldown_sec: float = 60.0,
    ) -> None:
        """Initialize the HTTP provider.

        Args:
            gateway_url: Base URL of the MemoryCore Gateway.
            api_key: Optional Bearer token for authentication.
            namespace: Service ID / namespace string ('craftdesk-dev').
            timeout_sec: Maximum HTTP request timeout in seconds.
            cooldown_sec: Seconds to enter circuit cooldown after consecutive failures.
        """
        self._gateway_url = gateway_url.rstrip("/")
        self._api_key = api_key
        self._namespace = namespace
        self._timeout_sec = timeout_sec
        self._cooldown_sec = cooldown_sec

        # Circuit breaker state
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._max_failures: int = 3

    def _is_in_cooldown(self) -> bool:
        """Check if circuit breaker is currently in cooldown state."""
        if self._failure_count >= self._max_failures:
            elapsed = time.time() - self._last_failure_time
            if elapsed < self._cooldown_sec:
                return True
            # Reset circuit breaker after cooldown period
            self._failure_count = 0
            self._last_failure_time = 0.0
        return False

    def _record_failure(self) -> None:
        """Record a network or service failure."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self._max_failures:
            logger.warning(
                f"[tencent_memory] Circuit opened: {self._failure_count} consecutive failures. "
                f"Cooldown active for {self._cooldown_sec}s."
            )

    def _record_success(self) -> None:
        """Record a successful response and reset circuit breaker."""
        self._failure_count = 0
        self._last_failure_time = 0.0

    def _get_headers(self) -> dict[str, str]:
        """Construct HTTP headers for MemoryCore requests."""
        api_key = self._api_key or "craftdesk-dev-key"
        return {
            "Content-Type": "application/json",
            "x-tdai-service-id": "default",
            "Authorization": f"Bearer {api_key}",
        }

    async def capture(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.GENERAL_KNOWLEDGE,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Capture a memory item via MemoryCore API.

        Args:
            content: Memory text string.
            category: Memory category enum.
            tags: Optional tags list.
            metadata: Optional metadata dict.

        Returns:
            True if stored successfully, False otherwise.
        """
        if self._is_in_cooldown():
            logger.debug("[tencent_memory] Capture skipped (circuit breaker cooldown)")
            return False

        try:
            import httpx

            url = f"{self._gateway_url}/capture"
            payload = {
                "user_content": "Capture new fact",
                "assistant_content": content,
                "session_key": "default",
                "metadata": metadata or {},
            }
            async with httpx.AsyncClient(timeout=self._timeout_sec) as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code in (200, 201):
                    self._record_success()
                    logger.info(
                        f"[tencent_memory] Captured memory ({category.value}): '{content[:40]}...'"
                    )
                    return True
                else:
                    logger.warning(
                        f"[tencent_memory] Capture failed HTTP {resp.status_code}: {resp.text[:100]}"
                    )
                    self._record_failure()
                    return False
        except Exception as exc:
            logger.warning(f"[tencent_memory] Capture request exception: {exc}")
            self._record_failure()
            return False

    async def recall(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Recall top-K relevant memories matching a query.

        Args:
            query: Context search query.
            limit: Maximum result count.

        Returns:
            List of matching MemoryEntry items, or empty list if unavailable.
        """
        if self._is_in_cooldown():
            logger.debug("[tencent_memory] Recall skipped (circuit breaker cooldown)")
            return []

        try:
            import httpx

            url = f"{self._gateway_url}/v2/atomic/search"
            payload = {
                "query": query,
                "limit": limit,
            }
            async with httpx.AsyncClient(timeout=self._timeout_sec) as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code == 200:
                    self._record_success()
                    envelope = resp.json()
                    data = (
                        envelope.get("data", {}) if isinstance(envelope, dict) else {}
                    )
                    raw_items = data.get("items", []) if isinstance(data, dict) else []
                    entries: list[MemoryEntry] = []
                    for item in raw_items:
                        entries.append(
                            MemoryEntry(
                                id=str(item.get("id", "")),
                                content=str(item.get("content", "")),
                                category=MemoryCategory(
                                    item.get("category", "general_knowledge")
                                ),
                                tags=item.get("tags", []),
                                relevance_score=float(item.get("score", 1.0)),
                                created_at=item.get("created_at"),
                                metadata=item.get("metadata", {}),
                            )
                        )
                    logger.info(
                        f"[tencent_memory] Recalled {len(entries)} items for query '{query[:30]}'"
                    )
                    return entries
                else:
                    logger.warning(
                        f"[tencent_memory] Recall HTTP {resp.status_code}: {resp.text[:100]}"
                    )
                    self._record_failure()
                    return []
        except Exception:
            logger.exception("[tencent_memory] Recall request exception")
            self._record_failure()
            return []

    async def search(
        self,
        query: str,
        category: MemoryCategory | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search stored memories by query with optional category filtering."""
        results = await self.recall(query, limit=limit)
        if category:
            return [m for m in results if m.category == category]
        return results

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory item by ID."""
        if self._is_in_cooldown():
            return False

        try:
            import httpx

            url = f"{self._gateway_url}/v2/atomic/delete"
            payload = {"ids": [memory_id]}
            async with httpx.AsyncClient(timeout=self._timeout_sec) as client:
                # v2 delete uses POST with request body or DELETE according to schemas
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code in (200, 204):
                    self._record_success()
                    return True
                self._record_failure()
                return False
        except Exception as exc:
            logger.warning(f"[tencent_memory] Delete request exception: {exc}")
            self._record_failure()
            return False

    async def health(self) -> dict[str, Any]:
        """Check status of MemoryCore Gateway."""
        try:
            import httpx

            url = f"{self._gateway_url}/health"
            async with httpx.AsyncClient(timeout=1.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    self._record_success()
                    return {
                        "status": "healthy",
                        "gateway_url": self._gateway_url,
                        "namespace": self._namespace,
                    }
        except Exception as exc:
            logger.debug(f"[tencent_memory] Health check failed: {exc}")
        return {
            "status": "unhealthy",
            "gateway_url": self._gateway_url,
            "namespace": self._namespace,
        }


class MockMemoryProvider(BaseMemoryProvider):
    """In-memory mock provider for testing and offline development."""

    def __init__(self) -> None:
        """Initialize mock storage dictionary."""
        self._memories: dict[str, MemoryEntry] = {}
        self._counter: int = 0

    async def capture(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.GENERAL_KNOWLEDGE,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store memory in local dict."""
        self._counter += 1
        mem_id = f"mock-{self._counter}"
        entry = MemoryEntry(
            id=mem_id,
            content=content,
            category=category,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._memories[mem_id] = entry
        return True

    async def recall(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Return items containing query keywords."""
        q_lower = query.lower()
        matches = []
        for item in self._memories.values():
            if q_lower in item.content.lower() or any(
                q_lower in tag.lower() for tag in item.tags
            ):
                matches.append(item)
        return matches[:limit]

    async def search(
        self,
        query: str,
        category: MemoryCategory | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search mock memories with category filter."""
        results = await self.recall(query, limit=limit)
        if category:
            return [m for m in results if m.category == category]
        return results

    async def delete(self, memory_id: str) -> bool:
        """Delete item from mock dict."""
        return self._memories.pop(memory_id, None) is not None

    async def health(self) -> dict[str, Any]:
        """Return healthy status for mock provider."""
        return {"status": "healthy", "provider": "mock", "count": len(self._memories)}
