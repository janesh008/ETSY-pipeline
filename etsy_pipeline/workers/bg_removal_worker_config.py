"""Background Removal Worker Configuration — constants for the bg_removal stage.

All hardcoded values for the bg_removal worker are stored here, never inline.

Responsibility: Configuration constants for rembg background removal and GPU cost tracking.
"""

from __future__ import annotations

# ------------------------------------------------------------------
# rembg AI Model Settings
# ------------------------------------------------------------------

REMBG_MODEL_NAME: str = "isnet-general-use"
"""Default rembg model architecture (isnet-general-use provides best quality for clipart)."""

CLEAR_GPU_EVERY_N_IMAGES: int = 25
"""Clear PyTorch CUDA cache and run gc.collect() every N images to avoid OOM."""

# ------------------------------------------------------------------
# Category Subfolder Names
# ------------------------------------------------------------------

MISC_CATEGORY_SUBFOLDER: str = "misc_category"
"""Subfolder containing character/prop cliparts requiring AI background removal."""

PATTERN_SCENE_BONUS_SUBFOLDER: str = "pattern_scene_bonus_category"
"""Subfolder containing pattern/scene/bonus cliparts that skip AI background removal."""

# ------------------------------------------------------------------
# GPU Cost Tracking
# ------------------------------------------------------------------

GPU_VM_HOURLY_RATE_USD: float = 0.75
"""Estimated hourly compute rate in USD for background removal processing."""

_PROGRESS_FLUSH_EVERY: int = 5
"""Flush progress updates to MongoDB every N processed images."""
