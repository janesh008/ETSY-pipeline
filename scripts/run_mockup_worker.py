"""CLI entry point for the Mockup & PDF worker.

Usage:
    # Process all PENDING mockup jobs in a loop (daemon mode):
    python scripts/run_mockup_worker.py --daemon

    # Process single job ID:
    python scripts/run_mockup_worker.py --job-id 997c27dc5566

    # Process PENDING and retry FAILED jobs:
    python scripts/run_mockup_worker.py --daemon --retry-failed
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

# Add project root to path for direct script execution
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from etsy_pipeline.config.settings import get_settings  # noqa: E402
from etsy_pipeline.models.job import Job  # noqa: E402
from etsy_pipeline.utils.logging import get_logger, setup_logging  # noqa: E402
from etsy_pipeline.workers.mockup_worker import MockupWorker  # noqa: E402

logger = get_logger(__name__)

_POLL_INTERVAL: int = 10
_FAILED_COOLDOWN_SECONDS: float = 300.0  # 5 minutes cooldown for failed jobs


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Mockup & PDF Worker — processes mockup jobs from MongoDB.",
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
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        default=False,
        help="Also query and retry FAILED jobs in addition to PENDING jobs (default: False).",
    )
    return parser.parse_args()


def process_single_job(job_id: str, store: Any, worker: MockupWorker) -> None:
    """Process a single specific MongoDB job ID."""
    doc = store._collection.find_one({"job_id": job_id})
    if not doc:
        logger.error(f"[run_mockup_worker] Job {job_id} not found in MongoDB.")
        sys.exit(1)

    logger.info(f"[run_mockup_worker] Processing job {job_id} ({doc.get('theme', '?')})")
    job = Job(
        job_id=job_id,
        theme=doc.get("theme", "unknown"),
        event_type=doc.get("event_type", "birthday"),
        date_folder=doc.get("date_folder", ""),
    )

    try:
        job = worker.run(job)
        store.update_stage_status(job_id, "mockups", "COMPLETED")
        store.upsert_job(job)
        logger.info(f"[run_mockup_worker] ✅ Completed job {job_id}")
    except Exception as exc:
        logger.error(f"[run_mockup_worker] ❌ Job {job_id} failed: {exc}")
        store.update_stage_status(
            job_id, "mockups", "FAILED", error_message=str(exc)
        )
        sys.exit(1)


def run_daemon_mode(settings: object, retry_failed: bool = False) -> None:
    """Poll MongoDB indefinitely for PENDING (or FAILED with cooldown) mockup jobs."""
    from etsy_pipeline.services.mongo_store import MongoJobStore

    try:
        store = MongoJobStore(settings=settings)  # type: ignore[arg-type]
    except Exception as exc:
        logger.error(f"[run_mockup_worker] Could not connect to MongoDB: {exc}")
        sys.exit(1)

    worker = MockupWorker(settings=settings, mongo_store=store)  # type: ignore[arg-type]

    failed_cooldown: dict[str, float] = {}
    target_statuses = ["PENDING", "FAILED"] if retry_failed else ["PENDING"]

    logger.info(
        f"[run_mockup_worker] Daemon mode started — polling MongoDB for statuses {target_statuses}..."
    )

    while True:
        try:
            pending_docs = store.list_jobs_by_stage_status(
                "mockups", target_statuses, limit=5
            )

            now = time.time()
            valid_docs = []
            for doc in pending_docs:
                jid = doc.get("job_id", "")
                if jid in failed_cooldown:
                    if now - failed_cooldown[jid] < _FAILED_COOLDOWN_SECONDS:
                        continue  # Skip jobs in cooldown
                    else:
                        del failed_cooldown[jid]
                valid_docs.append(doc)

            if not valid_docs:
                time.sleep(_POLL_INTERVAL)
                continue

            for doc in valid_docs:
                job_id: str = doc.get("job_id", "")
                if not job_id:
                    continue

                if not store.try_claim_stage(job_id, "mockups"):
                    continue

                logger.info(
                    f"[run_mockup_worker] Claimed job {job_id} ({doc.get('theme', '?')})"
                )

                job = Job(
                    job_id=job_id,
                    theme=doc.get("theme", "unknown"),
                    event_type=doc.get("event_type", "birthday"),
                    date_folder=doc.get("date_folder", ""),
                )

                try:
                    job = worker.run(job)
                    store.update_stage_status(job_id, "mockups", "COMPLETED")
                    store.upsert_job(job)
                    if job_id in failed_cooldown:
                        del failed_cooldown[job_id]
                    logger.info(f"[run_mockup_worker] ✅ Completed job {job_id}")
                except Exception as exc:
                    failed_cooldown[job_id] = time.time()
                    logger.error(f"[run_mockup_worker] ❌ Job {job_id} failed: {exc}")
                    store.update_stage_status(
                        job_id, "mockups", "FAILED", error_message=str(exc)
                    )

        except KeyboardInterrupt:
            logger.info("[run_mockup_worker] Daemon stopped by user (Ctrl+C)")
            break
        except Exception as exc:
            logger.error(f"[run_mockup_worker] Unexpected error: {exc}")
            time.sleep(_POLL_INTERVAL)


def main() -> None:
    """Main entry point."""
    args = parse_args()
    settings = get_settings()
    setup_logging(level=settings.log_level, log_format=settings.log_format)

    logger.info("[run_mockup_worker] Starting Mockup & PDF Worker")

    from etsy_pipeline.services.mongo_store import MongoJobStore
    if args.job_id:
        store = MongoJobStore(settings=settings)
        worker = MockupWorker(settings=settings, mongo_store=store)
        process_single_job(args.job_id, store, worker)
    else:
        run_daemon_mode(settings, retry_failed=args.retry_failed)


if __name__ == "__main__":
    main()
