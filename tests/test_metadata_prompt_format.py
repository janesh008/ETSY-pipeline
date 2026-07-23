"""Unit tests for Etsy listing generator prompt format and rules."""

from __future__ import annotations

from pathlib import Path


def test_master_prompt_contains_required_formatting_rules() -> None:
    """Verify Deepseek_etsy_listing_generator_prompt.txt contains required rules."""
    project_root = Path(__file__).resolve().parent.parent
    prompt_path = (
        project_root / "etsy_pipeline" / "resources" / "Deepseek_etsy_listing_generator_prompt.txt"
    )
    assert prompt_path.exists(), f"Master prompt missing at {prompt_path}"

    content = prompt_path.read_text(encoding="utf-8")

    # 1. Title at top of description rule
    assert "Listing Title Header" in content or "Full Generated Etsy Listing Title" in content

    # 2. 300 DPI resolution rule
    assert "300 DPI" in content

    # 3. Direct non-segregated clipart count rule
    assert "DO NOT segregate or break down" in content or "State the total count of clipart PNGs directly" in content

    # 4. Beautiful section header accents
    assert "✨ — HOOK — ✨" in content
    assert "📦 — PRODUCT DETAILS — 📦" in content
    assert "💻 — HOW TO DOWNLOAD — 💻" in content
    assert "🎨 — DESIGN DESCRIPTION — 🎨" in content
    assert "✨ — PERFECT FOR — ✨" in content
    assert "🌟 — WHY PIXEL BAR STUDIO — 🌟" in content
    assert "📜 — SEO REINFORCEMENT — 📜" in content
    assert "🛒 — CALL TO ACTION — 🛒" in content
