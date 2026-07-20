import sys
from pathlib import Path

# Add project root to sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from etsy_pipeline.config.settings import get_settings  # noqa: E402
from etsy_pipeline.services import GoogleDriveService  # noqa: E402
from etsy_pipeline.utils.logging import get_logger, setup_logging  # noqa: E402


def main():
    setup_logging(level="INFO")
    logger = get_logger("test_drive")

    settings = get_settings()

    # We will upload the existing file generated in the previous run
    # Path is relative to the root output directory: output/2026-07-19/Lilo_and_Stitch/Lilo_and_Stitch.txt
    local_file = (
        _PROJECT_ROOT
        / "output"
        / "2026-07-19"
        / "Lilo_and_Stitch"
        / "Lilo_and_Stitch.txt"
    )

    if not local_file.exists():
        # Fallback to scan output folder for any .txt file
        output_dir = _PROJECT_ROOT / "output"
        txt_files = list(output_dir.rglob("*.txt"))
        if txt_files:
            local_file = txt_files[0]
        else:
            logger.error(
                "No local prompt file found to test upload. Run prompt generation once first."
            )
            sys.exit(1)

    logger.info(f"Testing Google Drive Upload with file: {local_file}")

    try:
        drive_service = GoogleDriveService(settings=settings)
        file_id = drive_service.upload_file(local_file)
        logger.info(
            f"[SUCCESS] File uploaded successfully! Google Drive File ID: {file_id}"
        )
    except Exception as e:
        logger.error(f"[FAIL] Upload failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
