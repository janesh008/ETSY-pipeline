"""Unit tests for the Developer Memory Abstraction Layer."""

from __future__ import annotations

import pytest

from etsy_pipeline.config.settings import Settings
from etsy_pipeline.memory.base import MemoryCategory, MemoryEntry
from etsy_pipeline.memory.filter import MemoryFilter
from etsy_pipeline.memory.service import MemoryService
from etsy_pipeline.memory.tencent_provider import (
    MockMemoryProvider,
    TencentDBMemoryProvider,
)


@pytest.mark.asyncio
async def test_mock_memory_provider_operations() -> None:
    """Verify capture, recall, search, and delete operations on MockMemoryProvider."""
    provider = MockMemoryProvider()

    # Health check
    health = await provider.health()
    assert health["status"] == "healthy"

    # Capture
    success = await provider.capture(
        content="We use MongoJobStore with find_one_and_update for atomic claims",
        category=MemoryCategory.ARCHITECTURE,
        tags=["mongo", "atomic"],
    )
    assert success is True

    # Recall
    results = await provider.recall("find_one_and_update")
    assert len(results) == 1
    assert results[0].category == MemoryCategory.ARCHITECTURE
    assert "atomic claims" in results[0].content

    # Search with category filter
    search_results = await provider.search("mongo", category=MemoryCategory.ARCHITECTURE)
    assert len(search_results) == 1

    # Delete
    mem_id = results[0].id
    assert mem_id is not None
    deleted = await provider.delete(mem_id)
    assert deleted is True

    # Confirm deleted
    recalled = await provider.recall("find_one_and_update")
    assert len(recalled) == 0


def test_memory_filter_noise_rejection() -> None:
    """Verify MemoryFilter rejects low-value noise and stack traces."""
    mem_filter = MemoryFilter()

    # High signal -> True
    assert mem_filter.is_worth_remembering(
        "Workers in etsy_pipeline must be stateless and operate on Job model."
    ) is True

    # Too short -> False
    assert mem_filter.is_worth_remembering("short") is False

    # Stack trace -> False
    python_trace = """Traceback (most recent call last):
  File "main.py", line 12, in <module>
    run_pipeline()
ValueError: Invalid config"""
    assert mem_filter.is_worth_remembering(python_trace) is False

    # Installation command -> False
    assert mem_filter.is_worth_remembering("pip install pymongo httpx pydantic") is False


@pytest.mark.asyncio
async def test_memory_service_facade_format_for_prompt() -> None:
    """Verify MemoryService format_for_prompt produces clean Markdown output."""
    memories = [
        MemoryEntry(
            id="1",
            content="Workers must be stateless.",
            category=MemoryCategory.ARCHITECTURE,
        ),
        MemoryEntry(
            id="2",
            content="Etsy API requires X-API-Key header.",
            category=MemoryCategory.BUG_FIX,
        ),
    ]

    formatted = MemoryService.format_for_prompt(memories)
    assert "### Relevant Developer Context & Past Decisions:" in formatted
    assert "1. [ARCHITECTURE] Workers must be stateless." in formatted
    assert "2. [BUG_FIX] Etsy API requires X-API-Key header." in formatted


@pytest.mark.asyncio
async def test_memory_service_disabled_by_default() -> None:
    """Verify MemoryService returns empty lists gracefully when disabled."""
    settings = Settings(memory_enabled=False)
    service = MemoryService(settings=settings)

    assert service.is_enabled is False

    recalls = await service.recall("OAuth")
    assert recalls == []

    captured = await service.capture("Some decision", category=MemoryCategory.DECISION_LOG)
    assert captured is False


@pytest.mark.asyncio
async def test_tencent_provider_circuit_cooldown() -> None:
    """Verify TencentDBMemoryProvider circuit breaker enters cooldown on failure."""
    # Point provider to invalid port to trigger quick connection failure
    provider = TencentDBMemoryProvider(
        gateway_url="http://127.0.0.1:9999",
        timeout_sec=0.1,
        cooldown_sec=30.0,
    )

    # Force 3 failures to trip circuit
    for _ in range(3):
        await provider.recall("test")

    # Verify circuit is now open (cooldown active)
    assert provider._is_in_cooldown() is True

    # Calls during cooldown return immediately without making network calls
    results = await provider.recall("test")
    assert results == []
