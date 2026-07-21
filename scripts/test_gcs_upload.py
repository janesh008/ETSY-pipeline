"""Test utility to upload a prompt file to Google Cloud Storage.

Tests the GCS Store integration and path configuration without executing
the Gemini generation pipeline.

Usage:
    python scripts/test_gcs_upload.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path for direct script execution
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from etsy_pipeline.config.settings import get_settings  # noqa: E402
from etsy_pipeline.services.gcs_store import GCSStore  # noqa: E402
from etsy_pipeline.utils.logging import get_logger, setup_logging  # noqa: E402

logger = get_logger(__name__)


def main() -> None:
    """Initialize GCSStore and upload a dummy test file."""
    settings = get_settings()
    setup_logging(level=settings.log_level, log_format=settings.log_format)

    logger.info("Starting GCS Upload Test Script")
    logger.info(f"Target Bucket: {settings.gcs_bucket}")

    # 1. Create a dummy test file locally
    test_dir = _PROJECT_ROOT / "output" / "test_gcs"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / "test_prompt.txt"
    test_file.write_text(
        "## test_section\n\n1. This is a dummy test prompt for GCS validation.\n",
        encoding="utf-8",
    )
    logger.info(f"Created temporary local file: {test_file}")

    # 2. Upload using GCSStore
    try:
        gcs = GCSStore(settings=settings)

        # Build canonical path: Clipart/<date>/<theme>/<theme>.txt
        gcs_path = GCSStore.make_prompt_path("2026-07-20", "test_theme")
        logger.info(f"Uploading file to destination path: {gcs_path}")

        gcs_uri = gcs.upload_file(test_file, gcs_path)
        logger.info(f"[SUCCESS] Upload completed! GCS URI: {gcs_uri}")

    except Exception as exc:
        logger.error(f"[FAIL] Upload failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
