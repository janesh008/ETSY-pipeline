"""
CLI entry point for the Image Generation worker.

Run this on the GPU VM to start processing image generation jobs.
It continuously polls Firestore for PENDING jobs and generates images
using the local ComfyUI server.

Usage:
    # Process all PENDING image_generation jobs in a loop (daemon mode):
    python scripts/run_image_worker.py

    # Process a single specific job by job_id and exit:
    python scripts/run_image_worker.py --job-id abc123def456

    # Process prompts from a local .txt file (offline / local testing, no Firestore):
    python scripts/run_image_worker.py --prompt-file output/2026-07-20/Lilo_and_Stitch/Lilo_and_Stitch.txt

ComfyUI must be running locally on port 8188 before starting this script.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add project root to path for direct script execution
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from etsy_pipeline.config.settings import get_settings  # noqa: E402
from etsy_pipeline.models.job import Job, JobStatus  # noqa: E402
from etsy_pipeline.utils.logging import get_logger, setup_logging  # noqa: E402
from etsy_pipeline.workers.image_worker import ImageWorker  # noqa: E402

logger = get_logger(__name__)

# How long to wait between Firestore polls (seconds)
_POLL_INTERVAL: int = 10


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Image Generation Worker — runs ComfyUI jobs from the Firestore queue.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Daemon mode (runs forever, picks up Firestore jobs automatically):
  python scripts/run_image_worker.py

  # Process one specific job and exit:
  python scripts/run_image_worker.py --job-id abc123def456

  # Local testing — load prompt file directly (no Firestore required):
  python scripts/run_image_worker.py --prompt-file output/2026-07-20/Lilo_and_Stitch/Lilo_and_Stitch.txt \\
      --theme "Lilo & Stitch" --event birthday
        """,
    )
    parser.add_argument(
        "--job-id",
        type=str,
        default=None,
        help="Process a single specific Firestore job ID and exit.",
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        default=None,
        help="Path to a local prompt .txt file (offline mode — no Firestore). Requires --theme.",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        help="Theme name when using --prompt-file (e.g. 'Lilo & Stitch')",
    )
    parser.add_argument(
        "--event",
        type=str,
        default="birthday",
        help="Event type when using --prompt-file (default: birthday)",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        default=False,
        help="Run as a daemon — poll Firestore indefinitely for new jobs (default: True unless --job-id or --prompt-file given).",
    )
    return parser.parse_args()


def load_prompts_from_file(prompt_file: Path) -> dict[str, list[str]]:
    """Parse a prompt .txt file produced by run_prompts.py into a section dict.

    Args:
        prompt_file: Path to the local prompt .txt file.

    Returns:
        Dict of section_name -> list of prompt strings.
    """
    text = prompt_file.read_text(encoding="utf-8")
    prompts: dict[str, list[str]] = {}
    current_section: str | None = None

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("## "):
            current_section = line[3:].strip()
            prompts[current_section] = []
        elif current_section and line and line[0].isdigit() and ". " in line:
            _, prompt_text = line.split(". ", 1)
            prompts[current_section].append(prompt_text.strip())

    total = sum(len(v) for v in prompts.values())
    logger.info(f"[run_image_worker] Loaded {total} prompts from {prompt_file.name}")
    return prompts


def run_local_mode(args: argparse.Namespace, settings: object) -> None:
    """Run image generation from a local prompt file (no Firestore)."""
    if not args.theme:
        logger.error("[run_image_worker] --theme is required when using --prompt-file")
        sys.exit(1)

    prompt_file = Path(args.prompt_file)
    if not prompt_file.exists():
        logger.error(f"[run_image_worker] Prompt file not found: {prompt_file}")
        sys.exit(1)

    prompts = load_prompts_from_file(prompt_file)

    job = Job(theme=args.theme, event_type=args.event)
    job.prompts = prompts
    job.stages["prompt_generation"].mark_completed()

    worker = ImageWorker(settings=settings)  # type: ignore[arg-type]
    job = worker.run(job)

    print("\n" + "=" * 60)
    if job.status == JobStatus.COMPLETED:
        print("✅ IMAGE GENERATION COMPLETE")
    else:
        print("❌ IMAGE GENERATION FAILED")
    print("=" * 60)
    print(job.to_summary())


def run_daemon_mode(settings: object) -> None:
    """Poll MongoDB indefinitely for PENDING image_generation jobs."""
    from etsy_pipeline.services.mongo_store import MongoJobStore

    try:
        store = MongoJobStore(settings=settings)  # type: ignore[arg-type]
    except Exception as exc:
        logger.error(f"[run_image_worker] Could not connect to MongoDB: {exc}")
        logger.error("Set MONGO_URI in .env.")
        sys.exit(1)

    worker = ImageWorker(settings=settings, mongo_store=store)  # type: ignore[arg-type]

    logger.info(
        "[run_image_worker] Daemon mode started — polling MongoDB for PENDING jobs..."
    )
    logger.info(
        f"[run_image_worker] Poll interval: {_POLL_INTERVAL}s. Press Ctrl+C to stop."
    )

    while True:
        try:
            pending_docs = store.list_jobs_by_stage_status(
                "image_generation", "PENDING", limit=5
            )

            if not pending_docs:
                logger.debug(
                    "[run_image_worker] No PENDING image_generation jobs. Waiting..."
                )
                time.sleep(_POLL_INTERVAL)
                continue

            for doc in pending_docs:
                job_id: str = doc.get("job_id", "")
                if not job_id:
                    continue

                # Atomically claim this job
                if not store.try_claim_stage(job_id, "image_generation"):
                    logger.debug(
                        f"[run_image_worker] Could not claim {job_id} — already taken"
                    )
                    continue

                logger.info(
                    f"[run_image_worker] Claimed job {job_id} ({doc.get('theme', '?')})"
                )

                # Reconstruct minimal Job object from Firestore doc
                job = Job(
                    job_id=job_id,
                    theme=doc.get("theme", "unknown"),
                    event_type=doc.get("event_type", "birthday"),
                    date_folder=doc.get("date_folder", ""),
                )

                # Load prompts from GCS
                from etsy_pipeline.services.gcs_store import GCSStore

                gcs = GCSStore(settings=settings)  # type: ignore[arg-type]
                gcs_prompt_path = GCSStore.make_prompt_path(
                    job.date_folder, job.theme_slug
                )
                try:
                    prompt_text = gcs.download_as_text(gcs_prompt_path)
                    # Parse the prompt file
                    temp_file = Path(f"/tmp/{job.job_id}_prompts.txt")
                    temp_file.write_text(prompt_text, encoding="utf-8")
                    job.prompts = load_prompts_from_file(temp_file)
                    temp_file.unlink(missing_ok=True)
                except Exception as exc:
                    logger.error(
                        f"[run_image_worker] Failed to load prompts for {job_id}: {exc}"
                    )
                    store.update_stage_status(
                        job_id,
                        "image_generation",
                        "FAILED",
                        error_message=f"Could not load prompts from GCS: {exc}",
                    )
                    continue

                # Run generation
                try:
                    job = worker.run(job)
                    store.update_stage_status(job_id, "image_generation", "COMPLETED")
                    store.upsert_job(job)
                    logger.info(f"[run_image_worker] ✅ Completed job {job_id}")
                except Exception as exc:
                    logger.error(f"[run_image_worker] ❌ Job {job_id} failed: {exc}")
                    store.update_stage_status(
                        job_id, "image_generation", "FAILED", error_message=str(exc)
                    )

        except KeyboardInterrupt:
            logger.info("[run_image_worker] Daemon stopped by user (Ctrl+C)")
            break
        except Exception as exc:
            logger.error(f"[run_image_worker] Unexpected error in poll loop: {exc}")
            time.sleep(_POLL_INTERVAL)


def main() -> None:
    """Main entry point."""
    args = parse_args()
    settings = get_settings()
    setup_logging(level=settings.log_level, log_format=settings.log_format)

    logger.info("[run_image_worker] Starting Image Generation Worker")
    logger.info(
        f"[run_image_worker] GCP Project: {settings.gcp_project_id or '(not set)'}"
    )
    logger.info(f"[run_image_worker] GCS Bucket: {settings.gcs_bucket or '(not set)'}")

    if args.prompt_file:
        # Local/offline testing mode
        run_local_mode(args, settings)
    elif args.job_id:
        # Single-job mode: not yet implemented (Phase 2)
        logger.error(
            "--job-id mode not yet implemented. Use --prompt-file for local testing."
        )
        sys.exit(1)
    else:
        # Daemon mode: poll MongoDB indefinitely
        run_daemon_mode(settings)


if __name__ == "__main__":
    main()
