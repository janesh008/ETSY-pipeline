"""
Prompt worker configuration — constants and settings specific to prompt generation.

All SKILL.md-derived constants are centralized here so the worker
logic stays clean and configuration changes don't require code changes.
"""

from __future__ import annotations

# =============================================================
# LOCKED SECTION HEADINGS (from SKILL.md RULE A)
# =============================================================
# These are the ONLY valid section headings. They must appear
# exactly as spelled in the generated output. The order here
# matches the SKILL.md specification.

LOCKED_SECTIONS: list[str] = [
    "MAIN_CHARACTER",
    "SUB_CHARACTER_1",
    "SUB_CHARACTER_2",
    "SUB_CHARACTER_3",
    "SUB_CHARACTER_4",
    "SUB_CHARACTER_5",
    "SUB_CHARACTER_6",
    "SUB_CHARACTER_7",
    "SUB_CHARACTER_8",
    "CHARACTER_COMBO_2",
    "CHARACTER_COMBO_3",
    "CHARACTER_COMBO_4",
    "CHARACTER_COMBO_FULL_GROUP",
    "PATTERN",
    "PROP",
    "SCENE",
    "LOGO_EMBLEM",
    "BANNER",
    "ALPHABET_NUMBER",
    "FRAME_BORDER",
]

# Sections that are always active regardless of roster size
ALWAYS_ACTIVE_SECTIONS: list[str] = [
    "MAIN_CHARACTER",
    "PATTERN",
    "PROP",
    "SCENE",
]

# Sections that only activate when user asks for those product types
OPTIONAL_PRODUCT_SECTIONS: list[str] = [
    "LOGO_EMBLEM",
    "BANNER",
    "ALPHABET_NUMBER",
    "FRAME_BORDER",
]

# Character/combo sections (activated based on roster size)
CHARACTER_SECTIONS: list[str] = [
    "SUB_CHARACTER_1",
    "SUB_CHARACTER_2",
    "SUB_CHARACTER_3",
    "SUB_CHARACTER_4",
    "SUB_CHARACTER_5",
    "SUB_CHARACTER_6",
    "SUB_CHARACTER_7",
    "SUB_CHARACTER_8",
]

COMBO_SECTIONS: list[str] = [
    "CHARACTER_COMBO_2",
    "CHARACTER_COMBO_3",
    "CHARACTER_COMBO_4",
    "CHARACTER_COMBO_FULL_GROUP",
]

# =============================================================
# VALIDATION RULES (from SKILL.md)
# =============================================================

# RULE E — minimum prompts per active section
MIN_PROMPTS_PER_SECTION: int = 10

# Inactive section marker text
INACTIVE_SECTION_MARKER: str = "(not applicable for this roster)"

# =============================================================
# DEFAULT BUNDLE DISTRIBUTIONS (from SKILL.md STEP 5)
# =============================================================
# Key = roster_size, Value = {section: prompt_count}

DEFAULT_BUNDLE_DISTRIBUTIONS: dict[int, dict[str, int]] = {
    1: {
        "MAIN_CHARACTER": 65,
        "PATTERN": 20,
        "PROP": 30,
        "SCENE": 15,
    },
    2: {
        "MAIN_CHARACTER": 30,
        "SUB_CHARACTER_1": 25,
        "CHARACTER_COMBO_2": 20,
        "PATTERN": 15,
        "PROP": 25,
        "SCENE": 15,
    },
    3: {
        "MAIN_CHARACTER": 25,
        "SUB_CHARACTER_1": 20,
        "SUB_CHARACTER_2": 20,
        "CHARACTER_COMBO_2": 15,
        "CHARACTER_COMBO_3": 15,
        "PATTERN": 15,
        "PROP": 20,
        "SCENE": 15,
    },
    4: {
        "MAIN_CHARACTER": 25,
        "SUB_CHARACTER_1": 20,
        "SUB_CHARACTER_2": 20,
        "SUB_CHARACTER_3": 20,
        "CHARACTER_COMBO_4": 15,
        "PATTERN": 15,
        "PROP": 20,
        "SCENE": 15,
    },
}

# =============================================================
# GEMINI PROMPT CONSTRUCTION
# =============================================================

# Template for the user message sent to Gemini alongside the SKILL.md system instruction
USER_MESSAGE_TEMPLATE: str = (
    "Generate prompts for {theme} {event_type} theme, full bundle."
    "{style_clause}"
    "{count_clause}"
    "{sections_clause}"
)

STYLE_CLAUSE_TEMPLATE: str = " Use {style_hint} illustration style."
COUNT_CLAUSE_TEMPLATE: str = " Generate approximately {prompt_count} prompts total."
SECTIONS_CLAUSE_TEMPLATE: str = " Only generate these sections: {sections}."
