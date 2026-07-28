"""CraftDesk API — Prompt Engine powered directly by etsy_pipeline.workers.prompt_worker.PromptWorker."""

from __future__ import annotations

import os
from typing import Any

from etsy_pipeline.models.job import Job
from etsy_pipeline.workers.prompt_worker import PromptWorker
from etsy_pipeline.workers.prompt_worker_config import LOCKED_SECTIONS


class PromptEngineService:
    """Invokes etsy_pipeline PromptWorker to generate section-structured clipart prompts matching SKILL.md."""

    @classmethod
    async def generate_prompts(
        cls,
        theme_text: str = "",
        etsy_context: dict[str, Any] | None = None,
        reference_images: list[str] | None = None,
        prompt_count: int = 22,
        style_hint: str | None = None,
    ) -> dict[str, Any]:
        """Run PromptWorker.run(job) to generate prompts in exact SKILL.md locked section format.

        Returns dict containing:
        - job_id: str
        - theme: str
        - raw_prompt_text: str (exact SKILL.md output format with ## LOCKED_HEADINGS)
        - prompts: list[str]
        - sections: dict[str, list[str]]
        - character_roster: dict[str, str]
        - count: int
        - txt_content: str
        """
        # Determine theme title
        theme_title = theme_text.strip()
        if not theme_title and etsy_context:
            theme_title = etsy_context.get("title", "")
        if not theme_title:
            theme_title = "Watercolor Digital Clipart Set"

        # Determine style hint
        effective_style = style_hint or "watercolor clipart"
        if reference_images:
            effective_style += (
                f", matching visual style of {len(reference_images)} reference image(s)"
            )

        # Build Job instance for etsy_pipeline PromptWorker
        job = Job(
            theme=theme_title,
            event_type="birthday" if "birthday" in theme_title.lower() else "Normal",
            style_hint=effective_style,
            prompt_count=prompt_count,
        )

        try:
            worker = PromptWorker()
            job = worker.run(job)

            # Flatten section prompts for convenient array viewing
            flat_prompts: list[str] = []
            for sec_name, p_list in job.prompts.items():
                flat_prompts.extend(p_list)

            raw_text = job.raw_prompt_text or ""

            return {
                "job_id": job.job_id,
                "theme": job.theme,
                "raw_prompt_text": raw_text,
                "prompts": flat_prompts,
                "sections": job.prompts,
                "character_roster": job.character_roster,
                "count": len(flat_prompts),
                "txt_content": raw_text,
            }

        except Exception as err:
            # Fallback to structured SKILL.md format generator if API/config error occurs
            return cls._generate_skill_md_fallback(theme_title, prompt_count, str(err))

    @classmethod
    def _generate_skill_md_fallback(
        cls,
        theme: str,
        count: int,
        error_msg: str | None = None,
    ) -> dict[str, Any]:
        """Generate fallback output formatted strictly in SKILL.md locked section structure for exact `count` prompts."""
        actions = [
            "heroic action stance with flowing cape and golden belt",
            "holding a vibrant birthday cake with glowing candles and sparkles",
            "floating joyfully with colorful watercolor birthday balloons",
            "celebratory pose with falling gold confetti and gift box",
            "subtle watercolor splash background in gold and crimson",
            "holding golden lasso of truth with shimmering accents",
            "playful dynamic jump pose wearing a festive party hat",
            "sitting elegantly beside stacked birthday presents and ribbons",
            "waving warmly in watercolor portrait composition",
            "chibi style superhero pose blowing a party horn",
            "standing triumphant on a pedestal with glowing star emblem",
            "flying gracefully mid-air against soft cloud splatters",
            "holding a birthday banner with hand-drawn typography",
            "sitting cross-legged with a whimsical birthday card",
            "playful wink pose holding an oversized lollipop with birthday ribbons",
            "dynamic superhero landing pose with energetic pastel color splashes",
            "holding a sparkling birthday magic wand with golden trail",
            "wrapped in a decorative birthday ribbon with confetti pattern",
            "standing with arms crossed in confident cute chibi pose",
            "surrounded by a wreath of pastel watercolor flowers and stars",
            "holding a golden trophy cup with birthday celebration text",
            "floating on a fluffy watercolor cloud with golden stars",
            "cheering with pom-poms in vibrant watercolor splash style",
            "wearing a golden birthday crown with gemstone details",
            "holding a party blowout noise maker with festive ribbons",
            "sitting on a big birthday cake with burning candles",
            "blowing out birthday candles with smoke wisps and magic dust",
            "holding a festive balloon arch frame composition",
            "playful peek-a-boo pose from behind a big birthday gift box",
            "standing with cape fluttering in a soft pastel sunset gradient",
        ]

        lines: list[str] = [
            f"# CraftDesk AI Prompt Set — Pixel Bar Studio Cartoon Clipart — {theme}",
            f"# Total Target Prompts: {count}",
        ]
        if error_msg:
            lines.append(f"# Note: Generated via offline template engine ({error_msg})")
        lines.append("")

        sections: dict[str, list[str]] = {}
        flat_prompts: list[str] = []

        # Define active sections and target distribution
        active_sections = [
            "MAIN_CHARACTER",
            "SUB_CHARACTER_1",
            "SUB_CHARACTER_2",
            "SCENE",
            "PROP",
            "PATTERN",
            "LOGO_EMBLEM",
            "FRAME_BORDER",
        ]

        # Calculate prompts per active section
        base_per_sec = max(1, count // len(active_sections))
        remainder = count - (base_per_sec * len(active_sections))

        sec_targets: dict[str, int] = {}
        for idx, sec in enumerate(active_sections):
            extra = 1 if idx < remainder else 0
            sec_targets[sec] = base_per_sec + extra

        for sec in LOCKED_SECTIONS:
            target_num = sec_targets.get(sec, 0)
            lines.append(f"## {sec}")
            sec_prompts: list[str] = []

            if target_num > 0 and len(flat_prompts) < count:
                for i in range(target_num):
                    if len(flat_prompts) >= count:
                        break
                    idx = len(flat_prompts)
                    act = actions[idx % len(actions)]
                    variant = (idx // len(actions)) + 1
                    var_str = f" variation #{variant}" if variant > 1 else ""

                    p = (
                        f"Digital watercolor illustration of {theme}{var_str}, {act}, "
                        f"soft pastel watercolor splatters, isolated on transparent background, 300 DPI commercial quality."
                    )
                    sec_prompts.append(p)
                    flat_prompts.append(p)
                    lines.append(p)
                    lines.append("")
                sections[sec] = sec_prompts
            else:
                lines.append("(not applicable for this roster)")
                lines.append("")
                sections[sec] = []

        # If any remaining prompts to reach exact `count`, append to MAIN_CHARACTER
        while len(flat_prompts) < count:
            idx = len(flat_prompts)
            act = actions[idx % len(actions)]
            p = (
                f"Digital watercolor illustration of {theme} bonus pose #{idx + 1}, {act}, "
                f"soft pastel watercolor splatters, isolated on transparent background, 300 DPI commercial quality."
            )
            flat_prompts.append(p)
            sections["MAIN_CHARACTER"].append(p)

        raw_text = "\n".join(lines)

        return {
            "job_id": f"job-{count}-{os.urandom(4).hex()}",
            "theme": theme,
            "raw_prompt_text": raw_text,
            "prompts": flat_prompts,
            "sections": sections,
            "character_roster": {"MAIN_CHARACTER": theme},
            "count": len(flat_prompts),
            "txt_content": raw_text,
        }
