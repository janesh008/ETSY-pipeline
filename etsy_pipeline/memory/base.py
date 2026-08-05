"""Base memory abstraction models and interface definitions.

Defines the provider-agnostic interface and data models for developer memory storage.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MemoryCategory(StrEnum):
    """Categorization categories for developer memory entries."""

    ARCHITECTURE = "architecture"
    CODING_CONVENTION = "coding_convention"
    BUG_FIX = "bug_fix"
    DESIGN_PATTERN = "design_pattern"
    DECISION_LOG = "decision_log"
    GENERAL_KNOWLEDGE = "general_knowledge"


class MemoryEntry(BaseModel):
    """Data model representing a single memory item."""

    id: str | None = Field(default=None, description="Unique memory ID if persisted")
    content: str = Field(..., description="Memory content string")
    category: MemoryCategory = Field(
        default=MemoryCategory.GENERAL_KNOWLEDGE,
        description="Category classification",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Associated search tags",
    )
    relevance_score: float = Field(
        default=1.0,
        description="Relevance score (0.0 to 1.0) when retrieved via query",
    )
    created_at: str | None = Field(
        default=None,
        description="ISO-8601 creation timestamp",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context metadata",
    )


class BaseMemoryProvider(ABC):
    """Abstract base class for provider-agnostic memory storage implementations.

    All memory providers (TencentDB, Mock, Zep, Mem0, etc.) must implement this interface.
    """

    @abstractmethod
    async def capture(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.GENERAL_KNOWLEDGE,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Capture and store a new memory item.

        Args:
            content: The text content of the memory.
            category: Category classification of the memory.
            tags: Optional list of tag keywords.
            metadata: Optional additional key-value metadata.

        Returns:
            True if successfully captured, False otherwise.
        """
        ...

    @abstractmethod
    async def recall(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Recall relevant memory items matching a search query.

        Args:
            query: Free-text search query or context string.
            limit: Maximum number of memories to return.

        Returns:
            List of matching MemoryEntry items, ordered by relevance.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        category: MemoryCategory | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search memory items with optional category filtering.

        Args:
            query: Keyword or phrase query.
            category: Optional category filter.
            limit: Maximum results count.

        Returns:
            List of matching MemoryEntry items.
        """
        ...

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory item by its unique ID.

        Args:
            memory_id: Unique memory ID to delete.

        Returns:
            True if deleted, False otherwise.
        """
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Check provider health and connectivity status.

        Returns:
            Status dictionary containing 'status' ('healthy'|'unhealthy') and metrics.
        """
        ...
