"""Unit tests for MockupWorker integration with single_shop and multi_shop pipelines."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from etsy_pipeline.config.settings import Settings
from etsy_pipeline.models.job import Job
from etsy_pipeline.workers.mockup_worker import MockupWorker


def _create_valid_png(path: Path) -> None:
    """Create a small valid PNG file for PIL Image testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 255))
    img.save(path, format="PNG")


def test_mockup_worker_single_shop_defaults(tmp_path: Path) -> None:
    """Test MockupWorker targets pixelbarstudio for single_shop profile."""
    settings = Settings(
        output_root=str(tmp_path),
        project_root=str(Path(__file__).resolve().parent.parent),
    )
    worker = MockupWorker(settings=settings)

    job = Job(
        job_id="test_single_job_101",
        theme="baby_mickey",
        pipeline_profile="single_shop",
        selected_shops=["pixelbarstudio"],
    )

    # Setup valid dummy no_bg image file
    theme_dir = tmp_path / job.date_folder / job.theme_slug
    no_bg_dir = theme_dir / "no_bg"
    img_path = no_bg_dir / "baby_mickey_MAIN_CHARACTER_001.png"
    _create_valid_png(img_path)

    with patch.object(worker, "_run_mockup_creator") as mock_run:
        mock_run.return_value = [tmp_path / "mockup1.jpg"]
        with patch.object(worker, "_get_drive") as mock_drive:
            drive_instance = MagicMock()
            drive_instance.get_folder_id_by_path.return_value = "folder_123"
            drive_instance.share_folder_publicly.return_value = "http://drive.link/123"
            mock_drive.return_value = drive_instance

            with patch.object(worker, "_get_gcs") as mock_gcs:
                mock_gcs.return_value = None

                res_job = worker.run(job)
                mock_run.assert_called_once()
                call_args = mock_run.call_args
                assert call_args.kwargs.get("shops") == ["pixelbarstudio"]


def test_mockup_worker_multi_shop_pipeline(tmp_path: Path) -> None:
    """Test MockupWorker passes all selected shops for multi_shop profile."""
    settings = Settings(
        output_root=str(tmp_path),
        project_root=str(Path(__file__).resolve().parent.parent),
    )
    worker = MockupWorker(settings=settings)

    job = Job(
        job_id="test_multi_job_202",
        theme="baby_captain_america",
        pipeline_profile="multi_shop",
        selected_shops=["pixelbarstudio", "luna_cliparts", "crisp_png_co"],
    )

    # Setup valid dummy no_bg image file
    theme_dir = tmp_path / job.date_folder / job.theme_slug
    no_bg_dir = theme_dir / "no_bg"
    img_path = no_bg_dir / "cap_MAIN_CHARACTER_001.png"
    _create_valid_png(img_path)

    with patch.object(worker, "_run_mockup_creator") as mock_run:
        mock_run.return_value = [tmp_path / "mockup1.jpg", tmp_path / "mockup2.jpg"]
        with patch.object(worker, "_get_drive") as mock_drive:
            drive_instance = MagicMock()
            drive_instance.get_folder_id_by_path.return_value = "folder_456"
            drive_instance.share_folder_publicly.return_value = "http://drive.link/456"
            mock_drive.return_value = drive_instance

            with patch.object(worker, "_get_gcs") as mock_gcs:
                mock_gcs.return_value = None

                res_job = worker.run(job)
                mock_run.assert_called_once()
                call_args = mock_run.call_args
                assert call_args.kwargs.get("shops") == [
                    "pixelbarstudio",
                    "luna_cliparts",
                    "crisp_png_co",
                ]
