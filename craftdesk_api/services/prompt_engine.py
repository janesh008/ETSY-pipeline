"""CraftDesk API — Multi-input AI prompt generation engine using Gemini 2.5 Flash."""
from __future__ import annotations

import os
from typing import Any
from google import genai
from google.genai import types


class PromptEngineService:
    """Combines Text, Etsy listing context, and Reference Images to generate clipart prompts."""

    SYSTEM_INSTRUCTION = (
        "You are an expert AI prompt engineer specializing in high-converting commercial watercolor clipart "
        "bundles for Etsy. Create detailed, vivid, print-ready Midjourney/ComfyUI prompts for digital watercolor "
        "clipart sets. Each prompt must describe a unique character pose, action, or thematic element with "
        "vibrant color palettes, transparent background details, and isolated subject composition."
    )

    @classmethod
    async def generate_prompts(
        cls,
        theme_text: str = "",
        etsy_context: dict[str, Any] | None = None,
        reference_images: list[str] | None = None,
        prompt_count: int = 22,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Generate `prompt_count` clipart image prompts from multi-input sources.

        Returns dict containing:
        - prompts: list[str]
        - txt_content: str
        - prompt_count: int
        """
        # Determine API key
        gemini_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        # Build prompt synthesis context
        user_prompt_parts = []
        user_prompt_parts.append(f"Generate exactly {prompt_count} unique, high-resolution watercolor clipart prompts.\n")

        if theme_text:
            user_prompt_parts.append(f"PRIMARY THEME: {theme_text}\n")

        if etsy_context:
            user_prompt_parts.append("ETSY INSPIRATION CONTEXT:")
            user_prompt_parts.append(f"- Title: {etsy_context.get('title', '')}")
            user_prompt_parts.append(f"- Description Excerpt: {etsy_context.get('description', '')[:500]}\n")

        if reference_images:
            user_prompt_parts.append(f"REFERENCE IMAGE COUNT: {len(reference_images)} visual style reference(s) attached.\n")

        user_prompt_parts.append(
            f"FORMAT REQUIREMENT:\n"
            f"Output exactly {prompt_count} numbered prompts, one per line:\n"
            f"1. [Detailed watercolor clipart prompt description]\n"
            f"2. [Detailed watercolor clipart prompt description]\n"
            f"...\n"
            f"Do not include any conversational preamble or markdown code fences."
        )

        full_user_prompt = "\n".join(user_prompt_parts)

        # Fallback generator if API key is not configured in environment
        if not gemini_key or gemini_key.startswith("your-"):
            return cls._fallback_generate(theme_text, etsy_context, prompt_count)

        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=cls.SYSTEM_INSTRUCTION,
                    temperature=0.7,
                ),
            )
            raw_text = response.text or ""
            return cls._parse_response(raw_text, theme_text, prompt_count)

        except Exception as err:
            # Fallback on Gemini API error
            return cls._fallback_generate(theme_text, etsy_context, prompt_count, error_msg=str(err))

    @classmethod
    def _parse_response(cls, raw_text: str, theme: str, count: int) -> dict[str, Any]:
        """Parse Gemini output lines into a clean prompt array and .txt string."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        prompts: list[str] = []

        for line in lines:
            # Strip line numbers like "1. ", "01. ", "Prompt 1:"
            cleaned = line
            if cleaned[0].isdigit():
                cleaned = cleaned.lstrip("0123456789. :-")
            if cleaned:
                prompts.append(cleaned)

        # Truncate or extend to match target count
        if len(prompts) < count:
            base_theme = theme or "Watercolor Clipart"
            while len(prompts) < count:
                idx = len(prompts) + 1
                prompts.append(f"High-resolution digital watercolor clipart of {base_theme} pose #{idx}, vibrant colors, isolated on transparent background, 300 DPI, commercial use.")

        prompts = prompts[:count]

        # Build clean exportable .txt content
        txt_lines = [f"# CraftDesk AI Prompt Set — {theme or 'Custom Theme'}", f"# Total Prompts: {len(prompts)}", ""]
        for i, p in enumerate(prompts, start=1):
            txt_lines.append(f"[{i:02d}] {p}")

        return {
            "prompts": prompts,
            "txt_content": "\n".join(txt_lines),
            "count": len(prompts),
        }

    @classmethod
    def _fallback_generate(
        cls,
        theme: str,
        etsy_context: dict[str, Any] | None,
        count: int,
        error_msg: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured template prompts when offline or API key is not present."""
        base_subject = theme or (etsy_context.get("title") if etsy_context else "Wonder Woman Clipart")
        actions = [
            "heroic action stance with flowing cape",
            "holding a vibrant birthday cake with glowing candles",
            "floating with colorful birthday balloons",
            "joyful celebratory pose with confetti and gift box",
            "subtle watercolor splash background in gold and red",
            "holding a lasso of truth with gold glitter accent",
            "playful dynamic jump pose with festive party hat",
            "sitting elegantly with present and ribbons",
            "waving warmly in watercolor portrait composition",
            "chibi style superhero pose holding party horn",
        ]

        prompts: list[str] = []
        for i in range(count):
            act = actions[i % len(actions)]
            prompts.append(
                f"Digital watercolor illustration of {base_subject}, {act}, "
                f"soft pastel watercolor splatters, vibrant colors, isolated on white background, 300 DPI print-ready commercial quality."
            )

        txt_lines = [f"# CraftDesk AI Prompt Set — {base_subject}", f"# Total Prompts: {len(prompts)}", ""]
        if error_msg:
            txt_lines.append(f"# Note: Generated via offline template engine ({error_msg})")
            txt_lines.append("")

        for i, p in enumerate(prompts, start=1):
            txt_lines.append(f"[{i:02d}] {p}")

        return {
            "prompts": prompts,
            "txt_content": "\n".join(txt_lines),
            "count": len(prompts),
        }
