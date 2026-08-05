"""High-signal memory noise filter module.

Provides heuristic filtering to ensure low-value noise (stack traces, terminal outputs,
installation logs, ephemeral status lines) is discarded before writing to memory.
"""

from __future__ import annotations

import re

from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)

# Patterns that indicate noisy/unsuitable text for memory capture
_NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE),
    re.compile(r"pip install", re.IGNORECASE),
    re.compile(r"npm install", re.IGNORECASE),
    re.compile(r"passed in \d+\.\d+s", re.IGNORECASE),
    re.compile(r"^\s*at\s+[\w\.\$]+\s*\("),  # JS/TS stack trace line
    re.compile(r"File \".*\", line \d+, in ", re.IGNORECASE),  # Python stack trace line
    re.compile(r"^\s*[\-+]{3,}\s*$"),  # Diff separators
    re.compile(r"http://localhost:\d+", re.IGNORECASE),
]

# Keywords indicating high-value developer engineering insight
_HIGH_SIGNAL_KEYWORDS: set[str] = {
    "architecture",
    "pattern",
    "convention",
    "decision",
    "bug",
    "fix",
    "prefer",
    "rule",
    "always",
    "never",
    "schema",
    "pipeline",
    "stateless",
    "database",
    "oauth",
    "api",
}


class MemoryFilter:
    """Filters incoming text to determine whether it is high-signal enough to persist."""

    def __init__(self, min_length: int = 15, max_length: int = 2000) -> None:
        """Initialize the filter settings.

        Args:
            min_length: Minimum text character length.
            max_length: Maximum text character length.
        """
        self._min_length = min_length
        self._max_length = max_length

    def is_worth_remembering(self, content: str) -> bool:
        """Evaluate whether text content is worth capturing into developer memory.

        Args:
            content: Raw string content proposed for memory capture.

        Returns:
            True if content passes high-signal checks, False if rejected as noise.
        """
        if not content or not isinstance(content, str):
            return False

        stripped = content.strip()
        if len(stripped) < self._min_length:
            logger.debug(f"[memory_filter] Rejected: content too short ({len(stripped)} chars)")
            return False

        if len(stripped) > self._max_length:
            logger.debug(f"[memory_filter] Rejected: content too long ({len(stripped)} chars)")
            return False

        # Reject known noise patterns (stack traces, installation logs, etc.)
        for pattern in _NOISE_PATTERNS:
            if pattern.search(stripped):
                logger.debug(f"[memory_filter] Rejected: matched noise pattern '{pattern.pattern}'")
                return False

        return True

    def extract_keywords(self, content: str) -> list[str]:
        """Extract high-signal tags/keywords from text content.

        Args:
            content: Text to analyze.

        Returns:
            List of matching high-signal tags.
        """
        words = set(re.findall(r"\b[a-zA-Z]{3,}\b", content.lower()))
        matched = list(words.intersection(_HIGH_SIGNAL_KEYWORDS))
        return sorted(matched)
