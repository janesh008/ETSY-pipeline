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
    background_tasks.add_task(PipelineRunnerService.simulate_stage_execution, job_id, stage_name, False)

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


@router.websocket("/jobs/{job_id}/stream")
async def websocket_pipeline_stream(websocket: WebSocket, job_id: str) -> None:
    """WebSocket connection streaming real-time stage progress updates."""
    await websocket.accept()
    try:
        while True:
            job = PipelineRunnerService.get_job(job_id)
            if job:
                await websocket.send_json({
                    "job_id": job["job_id"],
                    "status": job["status"],
                    "current_stage": job["current_stage"],
                    "stages": job["stages"],
                })
                if job["status"] in ("completed", "failed"):
                    break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
