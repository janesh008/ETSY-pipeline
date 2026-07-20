"""Image Worker Configuration — constants for the ComfyUI image generation stage.

All hardcoded values for the image_worker are stored here, never inline.

Responsibility: Configuration constants for ComfyUI API interaction and GPU cost tracking.
"""

from __future__ import annotations

# ------------------------------------------------------------------
# ComfyUI Server
# ------------------------------------------------------------------

COMFYUI_HOST: str = "127.0.0.1"
"""ComfyUI server hostname — runs locally on the same GPU VM."""

COMFYUI_PORT: int = 8188
"""Default ComfyUI server port."""

COMFYUI_BASE_URL: str = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
"""Full ComfyUI API base URL."""

COMFYUI_PROMPT_ENDPOINT: str = f"{COMFYUI_BASE_URL}/prompt"
"""Endpoint to submit a new generation workflow."""

COMFYUI_HISTORY_ENDPOINT: str = f"{COMFYUI_BASE_URL}/history"
"""Endpoint to poll completed prompt results."""

COMFYUI_VIEW_ENDPOINT: str = f"{COMFYUI_BASE_URL}/view"
"""Endpoint to download a generated image by filename."""

# ------------------------------------------------------------------
# z_image_turbo Workflow — Node IDs from image_z_image_turbo1.json
# ------------------------------------------------------------------

WORKFLOW_JSON_PATH: str = "etsy_pipeline/resources/image_z_image_turbo1.json"
"""Path (relative to project root) to the ComfyUI API-format workflow JSON."""

WORKFLOW_PROMPT_NODE_ID: str = "57:27"
"""Node ID of the CLIPTextEncode node whose 'text' field receives the prompt."""

WORKFLOW_SEED_NODE_ID: str = "57:3"
"""Node ID of the KSampler node whose 'seed' field is randomised per image."""

WORKFLOW_SAVE_NODE_ID: str = "9"
"""Node ID of the SaveImage node (used to locate output file in /history)."""

# ------------------------------------------------------------------
# Generation Settings
# ------------------------------------------------------------------

COMFYUI_POLL_INTERVAL_SECONDS: float = 2.0
"""How often (in seconds) to poll the /history endpoint for job completion."""

COMFYUI_TIMEOUT_SECONDS: float = 300.0
"""Maximum time (in seconds) to wait for a single image before treating it as failed."""

COMFYUI_MAX_RETRIES: int = 3
"""Maximum number of retry attempts per prompt on ComfyUI failure."""

# ------------------------------------------------------------------
# GCS Path Prefixes
# ------------------------------------------------------------------

GCS_RAW_IMAGES_PREFIX: str = "raw_images"
"""GCS prefix for raw generated images (before bg removal)."""

# ------------------------------------------------------------------
# GPU Cost Tracking
# ------------------------------------------------------------------

GPU_VM_HOURLY_RATE_USD: float = 0.75
"""Estimated on-demand hourly cost of the n1-standard-8 + T4 GPU VM in USD.
Adjust this if you switch to Spot VMs (~$0.22/hr) or a different machine type."""

GPU_SPOT_HOURLY_RATE_USD: float = 0.22
"""Estimated Spot VM hourly cost (60-70% cheaper, interruptible)."""
