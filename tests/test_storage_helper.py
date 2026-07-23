"""Unit tests for storage_helper module."""

from __future__ import annotations

from pathlib import Path
from etsy_pipeline.config.settings import Settings
from etsy_pipeline.services.storage_helper import ensure_local_assets


def test_ensure_local_assets_vm_hit(tmp_path: Path) -> None:
    """Test ensure_local_assets returns immediately on local VM hit without downloading."""
    test_file = tmp_path / "0001.png"
    test_file.write_text("dummy_image_data")

    resolved = ensure_local_assets(
        local_dir=tmp_path,
        file_patterns=["*.png"],
    )

    assert len(resolved) == 1
    assert resolved[0] == test_file


def test_ensure_local_assets_empty_dir_no_remote(tmp_path: Path) -> None:
    """Test ensure_local_assets returns empty list when directory is empty and no remote specified."""
    resolved = ensure_local_assets(
        local_dir=tmp_path / "empty_subfolder",
        file_patterns=["*.png"],
    )

    assert resolved == []
