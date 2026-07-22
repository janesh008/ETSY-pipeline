"""Configuration constants for MetadataWorker (Phase 8 of the Etsy pipeline).

Defines validation rules, master prompt path, character limits, and
Etsy platform constraints.
"""

from __future__ import annotations

import re

# Gemini model for vision listing generation
GEMINI_MODEL: str = "gemini-2.5-flash"

# Relative path from project root to master listing prompt resource
MASTER_PROMPT_PATH: str = (
    "etsy_pipeline/resources/Deepseek_etsy_listing_generator_prompt.txt"
)

# Etsy Platform Constraints
TITLE_MAX_CHARS: int = 140
TAG_MAX_CHARS: int = 20
TAG_COUNT: int = 13
DESCRIPTION_MAX_CHARS: int = 102_400

# Chars allowed at most ONCE in Etsy title
TITLE_RESTRICTED_ONCE: set[str] = {"%", ":", "&", "+"}

# Regex for invalid title characters (forbidden: $, ^, `, emojis, HTML tags)
# Matches any character that is NOT a unicode letter, digit, punctuation, math symbol, or whitespace/trademark
TITLE_INVALID_CHARS_RE: re.Pattern[str] = re.compile(
    r"[^\w\s\.,!\?:\-\|/'\"()&%+™©®]", re.UNICODE
)

# Etsy taxonomy category search term for clip art
ETSY_DIGITAL_CATEGORY: str = "Clip Art"
