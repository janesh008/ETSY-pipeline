"""Unit tests for JPEG mockup detection and GCS upload in MockupWorker and PipelineRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from craftdesk_api.services.pipeline_runner import PipelineRunnerService
from etsy_pipeline.config.settings import Settings
from etsy_pipeline.models.job import Job
from etsy_pipeline.workers.mockup_worker import MockupWorker


def _create_dummy_jpg(path: Path) -> None:
    """Create a small valid JPG image file (>10KB) for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (300, 300), color=(200, 100, 50))
    img.save(path, format="JPEG", quality=90)


def test_mockup_worker_jpeg_collection_and_gcs_upload(tmp_path: Path) -> None:
    """Test MockupWorker collects .jpg files into job.mockups and uploads them to GCS."""
    settings = Settings(
        output_root=str(tmp_path),
        project_root=str(Path(__file__).resolve().parent.parent),
        gcs_bucket="test-bucket",
    )
    worker = MockupWorker(settings=settings)

    job = Job(
        job_id="test_jpeg_job_1",
        theme="Red_Jersey_Ronaldo",
        pipeline_profile="single_shop",
    )

    theme_dir = tmp_path / job.date_folder / job.theme_slug
    no_bg_dir = theme_dir / "no_bg"
    mockup_dir = theme_dir / "mockups"
    no_bg_dir.mkdir(parents=True, exist_ok=True)
    mockup_dir.mkdir(parents=True, exist_ok=True)

    _create_dummy_jpg(no_bg_dir / "preview.jpg")
    _create_dummy_jpg(mockup_dir / "Hero.jpg")
    _create_dummy_jpg(mockup_dir / "Main_character_1.jpg")

    mock_gcs = MagicMock()
    with patch.object(worker, "_get_gcs", return_value=mock_gcs):
        with patch.object(worker, "_get_drive") as mock_drive:
            drive_instance = MagicMock()
            drive_instance.get_folder_id_by_path.return_value = "folder_1"
            drive_instance.share_folder_publicly.return_value = "http://drive.link/1"
            mock_drive.return_value = drive_instance

            with patch.object(worker, "_run_mockup_creator") as mock_creator:
                # Return dummy rendered JPG mockups
                mock_creator.return_value = [
                    mockup_dir / "Hero.jpg",
                    mockup_dir / "Main_character_1.jpg",
                ]

                res_job = worker.run(job)

                # Verify JPG files are in job.mockups
                assert len(res_job.mockups) >= 2
                assert any(m.endswith(".jpg") for m in res_job.mockups)

                # Verify GCS upload_file was called for JPG mockups
                gcs_calls = [call[0][1] for call in mock_gcs.upload_file.call_args_list]
                assert any("mockups/Hero.jpg" in k for k in gcs_calls)


def test_is_stage_100pct_complete_detects_jpeg_mockups(tmp_path: Path) -> None:
    """Test _is_stage_100pct_complete detects .jpg mockups locally and prevents false-positive skips."""
    settings = Settings(
        output_root=str(tmp_path),
        project_root=str(Path(__file__).resolve().parent.parent),
    )

    job = Job(
        job_id="test_jpeg_job_2",
        theme="Red_Jersey_Ronaldo",
        pipeline_profile="multi_shop",
    )

    local_base = tmp_path / job.date_folder / job.theme_slug
    pdf_file = local_base / f"{job.theme_slug}.pdf"
    mockup_dir = local_base / "mockups"

    _create_dummy_jpg(pdf_file)
    for i in range(4):
        _create_dummy_jpg(mockup_dir / f"mockup_{i}.jpg")

    with patch("craftdesk_api.services.pipeline_runner.get_settings", return_value=settings):
        # Stage 'mockups' should return True when 4+ JPG mockups exist
        assert PipelineRunnerService._is_stage_100pct_complete(job, "mockups") is True
        # Stage 'multi_shop_mockups' should return True
        assert PipelineRunnerService._is_stage_100pct_complete(job, "multi_shop_mockups") is True
