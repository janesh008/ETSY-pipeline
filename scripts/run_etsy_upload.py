"""CLI entry point for triggering Etsy Open API v3 listing uploads (Shot 2).

Manual, human-triggered step executed after human review of consolidated CSV.

Usage:
    # Upload by MongoDB job ID:
    python scripts/run_etsy_upload.py --job-id 2d9ea9082812

    # Upload by theme name:
    python scripts/run_etsy_upload.py --theme "Wonder Woman"
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
from etsy_pipeline.models.job import Job  # noqa: E402
from etsy_pipeline.utils.logging import get_logger, setup_logging  # noqa: E402
from etsy_pipeline.workers.csv_worker import CSVWorker  # noqa: E402
from etsy_pipeline.workers.etsy_worker import EtsyWorker  # noqa: E402

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Etsy Listing Upload CLI — manually upload listings to Etsy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--job-id",
        type=str,
        default=None,
        help="Target MongoDB job ID to upload.",
    )
    parser.add_argument(
        "--theme",
        type=str,
        default=None,
        help="Target theme name to upload.",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    if not args.job_id and not args.theme:
        print("Error: Must specify either --job-id or --theme to trigger upload.")
        sys.exit(1)

    settings = get_settings()
    setup_logging(level=settings.log_level, log_format=settings.log_format)

    from etsy_pipeline.services.mongo_store import MongoJobStore

    try:
        store = MongoJobStore(settings=settings)
    except Exception as exc:
        logger.error(f"[run_etsy_upload] Could not connect to MongoDB: {exc}")
        sys.exit(1)

    # Find job document
    doc = None
    if args.job_id:
        doc = store._collection.find_one({"job_id": args.job_id})
    elif args.theme:
        doc = store._collection.find_one({"theme": args.theme})

    if not doc:
        logger.error(f"[run_etsy_upload] Job not found for input parameters.")
        sys.exit(1)

    job_id = doc.get("job_id", "")
    theme = doc.get("theme", "")
    logger.info(f"[run_etsy_upload] Found job {job_id} ({theme})")

    # Reconstruct Job object from MongoDB document
    job = Job(
        job_id=job_id,
        theme=theme,
        event_type=doc.get("event_type", "birthday"),
        date_folder=doc.get("date_folder", ""),
        pdf_drive_link=doc.get("pdf_drive_link"),
        etsy_title=doc.get("etsy_title"),
        etsy_description=doc.get("etsy_description"),
        etsy_tags=doc.get("etsy_tags", []),
        listing_price_usd=doc.get("listing_price_usd", 3.99),
        listing_quantity=doc.get("listing_quantity", 999),
    )

    etsy_worker = EtsyWorker(settings=settings)
    csv_worker = CSVWorker(settings=settings)

    try:
        # Run Etsy upload worker
        job = etsy_worker.run(job)
        store.update_stage_status(job_id, "etsy_upload", "COMPLETED")

        # Update consolidated CSV with listing ID and URL
        job = csv_worker.run(job)
        store.update_stage_status(job_id, "csv_generation", "COMPLETED")

        store.upsert_job(job)
        logger.info(f"[run_etsy_upload] 🎉 Listing published successfully!")
        logger.info(f"Listing ID:  {job.etsy_listing_id}")
        logger.info(f"Listing URL: {job.etsy_listing_url}")
    except Exception as exc:
        logger.error(f"[run_etsy_upload] ❌ Upload failed: {exc}")
        store.update_stage_status(
            job_id, "etsy_upload", "FAILED", error_message=str(exc)
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
