"""
CLI entry point for running the prompt generation stage.

Usage:
    python -m scripts.run_prompts --theme "Lilo & Stitch" --event birthday
    python -m scripts.run_prompts --theme "Minnie Mouse" --event "baby shower" --style watercolor
    python -m scripts.run_prompts --theme "Bluey" --count 150

Outputs:
    1. Prompts stored in the Job object (printed to console)
    2. Raw prompt text saved to output/<date>/<theme>/prompts.txt
    3. Job summary printed to console
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path for direct script execution
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from etsy_pipeline.config.settings import get_settings  # noqa: E402
from etsy_pipeline.models.job import Job, JobStatus  # noqa: E402
from etsy_pipeline.pipeline.orchestrator import Pipeline  # noqa: E402
from etsy_pipeline.utils.logging import get_logger, setup_logging  # noqa: E402

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate image prompts for Etsy clipart bundles using Gemini 2.5 Flash.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scripts.run_prompts --theme "Lilo & Stitch" --event birthday
  python -m scripts.run_prompts --theme "Minnie Mouse" --event "baby shower" --style watercolor
  python -m scripts.run_prompts --theme "Bluey" --count 150
        """,
    )
    parser.add_argument(
        "--theme",
        type=str,
        required=True,
        help="Cartoon/character theme name (e.g., 'Lilo & Stitch')",
    )
    parser.add_argument(
        "--event",
        type=str,
        default="birthday",
        help="Event theme (default: birthday)",
    )
    parser.add_argument(
        "--style",
        type=str,
        default=None,
        help="Optional style hint (e.g., 'watercolor', '3D', 'chibi')",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Optional total prompt count override",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output directory (default: from settings)",
    )
    return parser.parse_args()


def save_prompts_to_file(job: Job, output_dir: Path) -> Path:
    """
    Save the raw prompt text and parsed prompts to files.

    Creates:
        - prompts_raw.txt: Raw Gemini response
        - prompts.txt: Cleaned parsed prompts (backward compatible with queue_manager)

    Args:
        job: The completed Job with prompts.
        output_dir: Directory to save files to.

    Returns:
        Path to the saved prompts.txt file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save raw response
    if job.raw_prompt_text:
        raw_path = output_dir / "prompts_raw.txt"
        raw_path.write_text(job.raw_prompt_text, encoding="utf-8")
        logger.info(f"Raw prompt text saved to: {raw_path}")

    # Save parsed prompts in the format expected by the existing pipeline
    # This creates a .txt file compatible with queue_manager.ingest_new_prompt_files()
    prompts_path = output_dir / f"{job.theme.replace(' ', '_').replace('&', 'and')}.txt"

    lines: list[str] = []
    for section_name, section_prompts in job.prompts.items():
        if not section_prompts:
            continue
        lines.append(f"## {section_name}")
        lines.append("")
        for i, prompt in enumerate(section_prompts, 1):
            lines.append(f"{i}. {prompt}")
            lines.append("")

    prompts_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Parsed prompts saved to: {prompts_path}")

    return prompts_path


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Initialize settings and logging
    settings = get_settings()
    setup_logging(level=settings.log_level, log_format=settings.log_format)

    # Create a Job from CLI arguments
    job = Job(
        theme=args.theme,
        event_type=args.event,
        style_hint=args.style,
        prompt_count=args.count,
    )

    logger.info(f"Created job {job.job_id} for theme: '{job.theme}' ({job.event_type})")

    # Run the pipeline (currently only prompt generation)
    pipeline = Pipeline(settings=settings)
    job = pipeline.run(job)

    # Handle results
    if job.status == JobStatus.COMPLETED:
        # Determine output directory
        output_root = args.output_dir or settings.output_root
        output_dir = job.get_output_dir(output_root)

        # Save prompts to files
        prompts_path = save_prompts_to_file(job, output_dir)

        # Print summary
        print("\n" + "=" * 60)
        print("✅ PROMPT GENERATION COMPLETE")
        print("=" * 60)
        print(job.to_summary())
        print(f"\nPrompts saved to: {prompts_path}")
        print(f"Output directory: {output_dir}")

        # Print prompt distribution
        print("\n📊 Prompt Distribution:")
        for section, prompts in job.prompts.items():
            if prompts:
                print(f"  {section}: {len(prompts)} prompts")

        # Print character roster if found
        if job.character_roster:
            print("\n🎭 Character Roster:")
            for slot, desc in job.character_roster.items():
                print(f"  {slot}: {desc}")

    else:
        print("\n" + "=" * 60)
        print("❌ PROMPT GENERATION FAILED")
        print("=" * 60)
        print(job.to_summary())
        if job.errors:
            print("\nErrors:")
            for error in job.errors:
                print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
