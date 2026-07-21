"""Upscale Worker Configuration — constants for the upscaling stage.

All configuration details and settings for the upscaling worker are stored here.

Responsibility: Configuration constants for Real-ESRGAN upscaling and dynamic tile logic.
"""

from __future__ import annotations

# ── Google Drive Delivery Settings ─────────────────────────────────

ETSY_DRIVE_FOLDER_ID: str = "1JWUBqtP-PG-hRLEQj4Kh_vNzfb_G_PCP"
"""Parent folder ID of the ETSY directory on Google Drive."""

DRIVE_PATH_PARTS_PREFIX: list[str] = ["Clipart", "main_data"]
"""Prefix path parts for upscaled digital files delivery on Drive (e.g. Clipart/main_data/)."""

# ── Real-ESRGAN Model Settings ───────────────────────────────────

UPSCALE_MODEL_URL: str = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
"""URL to download the 4x-UltraSharp or default RealESRGAN weights if missing."""

TARGET_MAX_SIDE: int = 4096
"""Standard resolution target in pixels for the longest side."""

TARGET_DPI: int = 300
"""Target dots-per-inch (DPI) standard for print-ready digital downloads."""

START_TILE_SIZE: int = 512
"""Initial tile size for Real-ESRGAN processing. Automatically scales down on CUDA OOM."""

TILE_PAD: int = 32
PRE_PAD: int = 0

CLEAR_GPU_EVERY_N_IMAGES: int = 15
"""Interval of images processed before clearing CUDA cache to avoid VRAM leak."""

# ── Compute Cost Settings ─────────────────────────────────────────

GPU_VM_HOURLY_RATE_USD: float = 0.75
"""Estimated hourly compute rate in USD for upscaling GPU processing."""

_PROGRESS_FLUSH_EVERY: int = 5
"""Flush progress updates to MongoDB every N processed images."""
