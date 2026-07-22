"""CLI entry point for the Metadata Generation & CSV Consolidation worker.

Usage:
    # Process all PENDING metadata jobs in a loop (daemon mode):
    python scripts/run_metadata_worker.py --daemon
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
from etsy_pipeline.workers.csv_worker import CSVWorker  # noqa: E402
from etsy_pipeline.workers.metadata_worker import MetadataWorker  # noqa: E402

logger = get_logger(__name__)

_POLL_INTERVAL: int = 10


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Metadata & CSV Worker — processes metadata generation jobs from MongoDB.",
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
    """Poll MongoDB indefinitely for PENDING/FAILED metadata generation jobs."""
    from etsy_pipeline.services.mongo_store import MongoJobStore

    try:
        store = MongoJobStore(settings=settings)  # type: ignore[arg-type]
    except Exception as exc:
        logger.error(f"[run_metadata_worker] Could not connect to MongoDB: {exc}")
        sys.exit(1)

    metadata_worker = MetadataWorker(settings=settings, mongo_store=store)  # type: ignore[arg-type]
    csv_worker = CSVWorker(settings=settings)  # type: ignore[arg-type]

    logger.info(
        "[run_metadata_worker] Daemon mode started — polling MongoDB for metadata jobs..."
    )

    while True:
        try:
            pending_docs = store.list_jobs_by_stage_status(
                "metadata_generation", ["PENDING", "FAILED"], limit=5
            )

            if not pending_docs:
                time.sleep(_POLL_INTERVAL)
                continue

            for doc in pending_docs:
                job_id: str = doc.get("job_id", "")
                if not job_id:
                    continue

                if not store.try_claim_stage(job_id, "metadata_generation"):
                    continue

                logger.info(
                    f"[run_metadata_worker] Claimed job {job_id} ({doc.get('theme', '?')})"
                )

                job = Job(
                    job_id=job_id,
                    theme=doc.get("theme", "unknown"),
                    event_type=doc.get("event_type", "birthday"),
                    date_folder=doc.get("date_folder", ""),
                    pdf_drive_link=doc.get("pdf_drive_link"),
                )

                try:
                    # Run MetadataWorker
                    job = metadata_worker.run(job)
                    store.update_stage_status(job_id, "metadata_generation", "COMPLETED")

                    # Run CSVWorker
                    job = csv_worker.run(job)
                    store.update_stage_status(job_id, "csv_generation", "COMPLETED")

                    store.upsert_job(job)
                    logger.info(
                        f"[run_metadata_worker] ✅ Metadata & CSV complete for job {job_id}"
                    )
                except Exception as exc:
                    logger.error(
                        f"[run_metadata_worker] ❌ Job {job_id} metadata/csv failed: {exc}"
                    )
                    store.update_stage_status(
                        job_id, "metadata_generation", "FAILED", error_message=str(exc)
                    )

        except KeyboardInterrupt:
            logger.info("[run_metadata_worker] Daemon stopped by user (Ctrl+C)")
            break
        except Exception as exc:
            logger.error(f"[run_metadata_worker] Unexpected error: {exc}")
            time.sleep(_POLL_INTERVAL)


def main() -> None:
    """Main entry point."""
    parse_args()
    settings = get_settings()
    setup_logging(level=settings.log_level, log_format=settings.log_format)

    logger.info("[run_metadata_worker] Starting Metadata & CSV Worker")
    run_daemon_mode(settings)


if __name__ == "__main__":
    main()
