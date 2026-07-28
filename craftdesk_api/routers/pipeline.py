"""CraftDesk API — 6-Stage Pipeline execution router."""

from __future__ import annotations

import asyncio

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
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

    return PipelineJobResponse(
        job_id=job_id,
        user_id=user_id,
        theme_name=job_data["theme_name"],
        status=job_data["status"],
        current_stage=job_data["current_stage"],
        stages=[StageStatus(**s) for s in job_data["stages"]],
        hero_image_url=job_data["hero_image_url"],
        created_at=job_data["created_at"],
    )


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

    return PipelineJobResponse(
        job_id=job["job_id"],
        user_id=job["user_id"],
        theme_name=job["theme_name"],
        status=job["status"],
        current_stage=job["current_stage"],
        stages=[StageStatus(**s) for s in job["stages"]],
        hero_image_url=job["hero_image_url"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
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

    return PipelineJobResponse(
        job_id=job["job_id"],
        user_id=job["user_id"],
        theme_name=job["theme_name"],
        status=job["status"],
        current_stage=job["current_stage"],
        stages=[StageStatus(**s) for s in job["stages"]],
        hero_image_url=job["hero_image_url"],
        created_at=job["created_at"],
    )


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
    return PipelineJobResponse(
        job_id=stopped_job["job_id"],
        user_id=stopped_job["user_id"],
        theme_name=stopped_job["theme_name"],
        status=stopped_job["status"],
        current_stage=stopped_job["current_stage"],
        stages=[StageStatus(**s) for s in stopped_job["stages"]],
        hero_image_url=stopped_job["hero_image_url"],
        created_at=stopped_job["created_at"],
    )


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
