"""CraftDesk API — 6-Stage Pipeline execution router."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from craftdesk_api.db.base import get_db
from craftdesk_api.routers.gcp import get_current_user_id
from craftdesk_api.schemas.pipeline import (
    PipelineJobResponse,
    PipelineStartRequest,
    StageStatus,
)
from craftdesk_api.services.pipeline_runner import PipelineRunnerService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _build_job_response(job: dict[str, Any]) -> PipelineJobResponse:
    """Helper to convert job_data dict into PipelineJobResponse pydantic model."""
    return PipelineJobResponse(
        job_id=job["job_id"],
        user_id=job["user_id"],
        theme_name=job["theme_name"],
        status=job["status"],
        current_stage=job["current_stage"],
        stages=[StageStatus(**s) for s in job["stages"]],
        hero_image_url=job.get("hero_image_url"),
        mockups=job.get("mockups", []),
        pdf_drive_link=job.get("pdf_drive_link"),
        pdf_local_path=job.get("pdf_local_path"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
    )


@router.post(
    "/jobs",
    response_model=PipelineJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new 6-stage CraftDesk pipeline execution job",
)
async def start_pipeline_job(
    body: PipelineStartRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> PipelineJobResponse:
    """Start 6-stage asset generation pipeline (Image Gen, BG Removal, Upscale, Mockups, PDF, Metadata)."""
    job_data = PipelineRunnerService.create_job(
        user_id=user_id,
        theme_name=body.theme_name,
        prompts=body.prompts,
        prompt_file_path=body.prompt_file_path,
    )

    job_id = job_data["job_id"]
    # Trigger background pipeline runner
    background_tasks.add_task(PipelineRunnerService.run_full_pipeline_async, job_id)

    return _build_job_response(job_data)


@router.get(
    "/jobs/{job_id}",
    response_model=PipelineJobResponse,
    summary="Get pipeline job status and 6-stage progress",
)
async def get_pipeline_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> PipelineJobResponse:
    """Fetch status, per-stage progress %, root errors, and output metadata for a pipeline job."""
    job = PipelineRunnerService.get_job(job_id)
    if not job or job["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline job not found or access denied.",
        )

    return _build_job_response(job)


@router.get(
    "/jobs/{job_id}/pdf",
    summary="Download the generated clickable PDF wrapper for a pipeline job",
)
async def download_pipeline_job_pdf(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Return the generated A4 Clickable Catalog PDF wrapper as a downloadable file."""
    job = PipelineRunnerService.get_job(job_id)
    if not job or job["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline job not found.",
        )

    pdf_path = job.get("pdf_local_path")
    target_file: Path | None = Path(pdf_path) if pdf_path else None

    if not target_file or not target_file.exists():
        from etsy_pipeline.config.settings import get_settings

        settings = get_settings()
        date_folder = job.get("date_folder", "")
        theme_slug = job.get("theme_name", "").replace(" ", "_")
        possible_local = [
            Path(settings.output_root) / date_folder / theme_slug / f"{theme_slug}.pdf",
            Path(settings.output_root) / "Clipart" / date_folder / theme_slug / f"{theme_slug}.pdf",
        ]
        for p in possible_local:
            if p.exists():
                target_file = p
                break

        if (not target_file or not target_file.exists()) and settings.gcs_bucket:
            try:
                from etsy_pipeline.services.gcs_store import GCSStore

                gcs = GCSStore(settings=settings)
                gcs_key = f"Clipart/{date_folder}/{theme_slug}/pdf/{theme_slug}.pdf"
                local_dest = (
                    Path(settings.output_root) / date_folder / theme_slug / f"{theme_slug}.pdf"
                )
                local_dest.parent.mkdir(parents=True, exist_ok=True)
                gcs.download_file(gcs_key, local_dest)
                if local_dest.exists():
                    target_file = local_dest
            except Exception:
                pass

    if not target_file or not target_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found for this job. Ensure Stage 5 (Clickable PDF Wrap) has completed.",
        )

    return FileResponse(
        path=str(target_file),
        media_type="application/pdf",
        filename=target_file.name,
    )


@router.get(
    "/jobs/{job_id}/stages",
    response_model=list[StageStatus],
    summary="Get 6-stage status array",
)
async def get_job_stages(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> list[StageStatus]:
    """List per-stage progress %, failure states, and stderr logs."""
    job = PipelineRunnerService.get_job(job_id)
    if not job or job["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline job not found.",
        )
    return [StageStatus(**s) for s in job["stages"]]


@router.post(
    "/jobs/{job_id}/stages/{stage_name}/retry",
    response_model=PipelineJobResponse,
    summary="Retry a specific failed pipeline stage",
)
async def retry_failed_stage(
    job_id: str,
    stage_name: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
) -> PipelineJobResponse:
    """Re-queue a single failed stage without restarting the whole pipeline."""
    job = PipelineRunnerService.get_job(job_id)
    if not job or job["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline job not found.",
        )

    stage = next((s for s in job["stages"] if s["stage_name"] == stage_name), None)
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stage name: {stage_name}",
        )

    # Reset stage state
    stage["status"] = "pending"
    stage["progress_percent"] = 0
    stage["error_message"] = None
    stage["stderr_log"] = None
    job["status"] = "running"
    job["current_stage"] = stage_name

    # Trigger async stage simulation without failing
    background_tasks.add_task(
        PipelineRunnerService.simulate_stage_execution, job_id, stage_name, False
    )

    return _build_job_response(job)


@router.post(
    "/jobs/{job_id}/stop",
    response_model=PipelineJobResponse,
    summary="Stop a running pipeline execution job",
)
async def stop_pipeline_job(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> PipelineJobResponse:
    """Stop/cancel a running pipeline execution job immediately."""
    job = PipelineRunnerService.get_job(job_id)
    if not job or job["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline job not found.",
        )

    stopped_job = PipelineRunnerService.stop_job(job_id) or job
    return _build_job_response(stopped_job)


@router.websocket("/jobs/{job_id}/stream")
async def websocket_pipeline_stream(websocket: WebSocket, job_id: str) -> None:
    """WebSocket connection streaming real-time stage progress updates."""
    await websocket.accept()
    try:
        while True:
            job = PipelineRunnerService.get_job(job_id)
            if job:
                await websocket.send_json(
                    {
                        "job_id": job["job_id"],
                        "status": job["status"],
                        "current_stage": job["current_stage"],
                        "stages": job["stages"],
                    }
                )
                if job["status"] in ("completed", "failed"):
                    break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# ComfyUI process management
# ---------------------------------------------------------------------------
import os
import signal
import socket
import subprocess

# Store the ComfyUI process handle in memory (single-process server assumption)
_comfyui_process: subprocess.Popen | None = None

COMFYUI_DIR = os.getenv("COMFYUI_DIR", "/opt/ComfyUI")
COMFYUI_PYTHON = os.getenv("COMFYUI_PYTHON", f"{COMFYUI_DIR}/venv/bin/python")
COMFYUI_HOST = "127.0.0.1"
COMFYUI_PORT = 8188


def _is_comfyui_running() -> bool:
    """Return True if something is already listening on COMFYUI_PORT."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex((COMFYUI_HOST, COMFYUI_PORT)) == 0


@router.post(
    "/comfyui/start",
    summary="Start ComfyUI on the GPU VM (port 8188)",
)
async def start_comfyui(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Launch ComfyUI as a background process on the VM if not already running."""
    global _comfyui_process

    if _is_comfyui_running():
        return {
            "status": "already_running",
            "message": "ComfyUI is already listening on port 8188.",
        }

    log_path = f"{COMFYUI_DIR}/comfyui.log"
    try:
        log_file = open(log_path, "a")
        _comfyui_process = subprocess.Popen(
            [
                COMFYUI_PYTHON,
                "main.py",
                "--listen",
                COMFYUI_HOST,
                "--port",
                str(COMFYUI_PORT),
            ],
            cwd=COMFYUI_DIR,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,  # Detach from parent so killing uvicorn doesn't kill ComfyUI
        )
        # Give it a moment to start
        await asyncio.sleep(2)
        if _is_comfyui_running():
            return {
                "status": "started",
                "message": f"ComfyUI started (PID {_comfyui_process.pid}). Log: {log_path}",
            }
        else:
            return {
                "status": "starting",
                "message": f"ComfyUI launched (PID {_comfyui_process.pid}) — still initializing, check in a few seconds.",
            }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ComfyUI not found at '{COMFYUI_DIR}'. Set COMFYUI_DIR env var to the correct path.",
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start ComfyUI: {err!s}",
        )


@router.get(
    "/comfyui/status",
    summary="Check if ComfyUI is running on port 8188",
)
async def comfyui_status(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Return whether ComfyUI is currently listening on port 8188."""
    running = _is_comfyui_running()
    pid = (
        _comfyui_process.pid
        if (_comfyui_process and _comfyui_process.poll() is None)
        else None
    )
    return {
        "running": running,
        "pid": pid,
        "host": COMFYUI_HOST,
        "port": COMFYUI_PORT,
        "comfyui_dir": COMFYUI_DIR,
    }


@router.post(
    "/comfyui/stop",
    summary="Stop the ComfyUI process started via /comfyui/start",
)
async def stop_comfyui(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Terminate the ComfyUI background process if it was started via this API."""
    global _comfyui_process
    if _comfyui_process and _comfyui_process.poll() is None:
        try:
            os.killpg(os.getpgid(_comfyui_process.pid), signal.SIGTERM)
            _comfyui_process = None
            return {"status": "stopped", "message": "ComfyUI process terminated."}
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to stop ComfyUI: {err!s}",
            )
    if not _is_comfyui_running():
        return {"status": "not_running", "message": "ComfyUI was not running."}
    return {
        "status": "unknown",
        "message": "ComfyUI may have been started outside this API — stop it manually.",
    }
