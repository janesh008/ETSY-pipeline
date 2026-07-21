"""CLI entry point for the Background Removal worker.

Run this on the VM or local machine to process background removal jobs.
It polls MongoDB for PENDING/FAILED `bg_removal` jobs and removes backgrounds.

Usage:
    # Process all PENDING bg_removal jobs in a loop (daemon mode):
    python scripts/run_bg_removal_worker.py --daemon

    # Process a single specific job by job_id and exit:
    python scripts/run_bg_removal_worker.py --job-id abc123def456
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
from etsy_pipeline.models.job import Job  # noqa: E402
from etsy_pipeline.utils.logging import get_logger, setup_logging  # noqa: E402
from etsy_pipeline.workers.bg_removal_worker import (  # noqa: E402
    BackgroundRemovalWorker,
)

logger = get_logger(__name__)

_POLL_INTERVAL: int = 10


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Background Removal Worker — processes bg_removal jobs from MongoDB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--job-id",
        type=str,
        default=None,
        help="Process a single specific MongoDB job ID and exit.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        default=True,
        help="Run as a daemon — poll MongoDB indefinitely for new jobs (default: True).",
    )
    return parser.parse_args()


def run_daemon_mode(settings: object) -> None:
    """Poll MongoDB indefinitely for PENDING/FAILED bg_removal jobs."""
    from etsy_pipeline.services.mongo_store import MongoJobStore

    try:
        store = MongoJobStore(settings=settings)  # type: ignore[arg-type]
    except Exception as exc:
        logger.error(f"[run_bg_removal_worker] Could not connect to MongoDB: {exc}")
        logger.error("Set MONGO_URI in .env.")
        sys.exit(1)

    worker = BackgroundRemovalWorker(settings=settings, mongo_store=store)  # type: ignore[arg-type]

    logger.info(
        "[run_bg_removal_worker] Daemon mode started — polling MongoDB for bg_removal jobs..."
    )
    logger.info(
        f"[run_bg_removal_worker] Poll interval: {_POLL_INTERVAL}s. Press Ctrl+C to stop."
    )

    while True:
        try:
            pending_docs = store.list_jobs_by_stage_status(
                "bg_removal", ["PENDING", "FAILED"], limit=5
            )

            if not pending_docs:
                logger.debug(
                    "[run_bg_removal_worker] No PENDING or FAILED bg_removal jobs. Waiting..."
                )
                time.sleep(_POLL_INTERVAL)
                continue

            for doc in pending_docs:
                job_id: str = doc.get("job_id", "")
                if not job_id:
                    continue

                # Atomically claim this job
                if not store.try_claim_stage(job_id, "bg_removal"):
                    logger.debug(
                        f"[run_bg_removal_worker] Could not claim {job_id} — already taken"
                    )
                    continue

                logger.info(
                    f"[run_bg_removal_worker] Claimed job {job_id} ({doc.get('theme', '?')})"
                )

                job = Job(
                    job_id=job_id,
                    theme=doc.get("theme", "unknown"),
                    event_type=doc.get("event_type", "birthday"),
                    date_folder=doc.get("date_folder", ""),
                )

                try:
                    job = worker.run(job)
                    store.update_stage_status(job_id, "bg_removal", "COMPLETED")
                    store.upsert_job(job)
                    logger.info(f"[run_bg_removal_worker] ✅ Completed job {job_id}")
                except Exception as exc:
                    logger.error(
                        f"[run_bg_removal_worker] ❌ Job {job_id} failed: {exc}"
                    )
                    store.update_stage_status(
                        job_id, "bg_removal", "FAILED", error_message=str(exc)
                    )

        except KeyboardInterrupt:
            logger.info("[run_bg_removal_worker] Daemon stopped by user (Ctrl+C)")
            break
        except Exception as exc:
            logger.error(f"[run_bg_removal_worker] Unexpected error: {exc}")
            time.sleep(_POLL_INTERVAL)


def main() -> None:
    """Main entry point."""
    parse_args()
    settings = get_settings()
    setup_logging(level=settings.log_level, log_format=settings.log_format)

    logger.info("[run_bg_removal_worker] Starting Background Removal Worker")
    logger.info(
        f"[run_bg_removal_worker] GCS Bucket: {settings.gcs_bucket or '(not set)'}"
    )

    run_daemon_mode(settings)


if __name__ == "__main__":
    main()
