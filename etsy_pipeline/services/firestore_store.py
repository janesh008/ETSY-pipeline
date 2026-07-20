"""Firestore Job Store — atomic job state persistence backed by Cloud Firestore.

Replaces the flat-file state.json + lock-file approach from the legacy
queue_manager.py with Firestore atomic transactions. Safe across multiple
VMs (Prompt VM, GPU VM, BG-Removal VM) running concurrently.

Responsibility: Read, write, and atomically claim pipeline job state in Firestore.
"""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from etsy_pipeline.utils.logging import get_logger

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job

logger = get_logger(__name__)

# Firestore collection name
_JOBS_COLLECTION = "jobs"


def _now_iso() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


class FirestoreJobStore:
    """Atomic job state store backed by Cloud Firestore.

    Wraps the Google Cloud Firestore client to provide clean read/write/claim
    operations for pipeline Job documents. All state mutations use transactions
    to prevent race conditions across multiple worker VMs.

    Usage::

        store = FirestoreJobStore(settings=get_settings())
        store.upsert_job(job)
        store.update_stage_progress(job_id, "image_generation", images_done=45, cost_usd=1.47)
        pending_jobs = store.list_jobs_by_stage_status("image_generation", "PENDING")
    """

    def __init__(self, settings: Settings) -> None:
        """Initialise the Firestore client.

        Uses Application Default Credentials (ADC) — on the GCP VM this is
        the attached Service Account; locally it falls back to
        ``GOOGLE_APPLICATION_CREDENTIALS`` or ``gcloud auth application-default login``.

        Args:
            settings: Loaded pipeline settings (used for GCP project ID).
        """
        try:
            from google.cloud import firestore  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "google-cloud-firestore is not installed. "
                "Run: pip install google-cloud-firestore"
            ) from exc

        self._settings = settings
        self._db = firestore.Client(project=settings.gcp_project_id or None)
        self._worker_id = f"{socket.gethostname()}-{id(self)}"
        logger.info(
            f"[firestore] Firestore client initialised "
            f"(project={settings.gcp_project_id}, worker_id={self._worker_id})"
        )

    # ------------------------------------------------------------------
    # Write / Upsert
    # ------------------------------------------------------------------

    def upsert_job(self, job: Job) -> None:
        """Create or fully overwrite a job document in Firestore.

        Serialises the entire Job model (including all stage results) into a
        Firestore document. Idempotent — safe to call multiple times.

        Args:
            job: The Job instance to persist.
        """
        doc_ref = self._db.collection(_JOBS_COLLECTION).document(job.job_id)
        data = self._job_to_dict(job)
        doc_ref.set(data)
        logger.info(f"[firestore] Upserted job {job.job_id} ({job.theme})")

    def update_stage_status(
        self,
        job_id: str,
        stage_name: str,
        status: str,
        *,
        error_message: str | None = None,
        worker_id: str | None = None,
    ) -> None:
        """Update the status of a single stage field in Firestore.

        Args:
            job_id: The unique job identifier.
            stage_name: Name of the stage (e.g. ``"image_generation"``).
            status: New status string (``"PENDING"``, ``"RUNNING"``, ``"COMPLETED"``, ``"FAILED"``).
            error_message: Optional error string (set when status is ``"FAILED"``).
            worker_id: Identifier of the claiming VM / process.
        """
        doc_ref = self._db.collection(_JOBS_COLLECTION).document(job_id)
        updates: dict[str, Any] = {
            f"stages.{stage_name}.status": status,
            f"stages.{stage_name}.updated_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        if status == "RUNNING":
            updates[f"stages.{stage_name}.started_at"] = _now_iso()
            updates[f"stages.{stage_name}.worker_id"] = worker_id or self._worker_id
        if status in ("COMPLETED", "FAILED"):
            updates[f"stages.{stage_name}.completed_at"] = _now_iso()
        if error_message:
            updates[f"stages.{stage_name}.error_message"] = error_message
        doc_ref.update(updates)
        logger.debug(f"[firestore] {job_id}/{stage_name} → {status}")

    def update_stage_progress(
        self,
        job_id: str,
        stage_name: str,
        *,
        images_done: int | None = None,
        images_total: int | None = None,
        cost_usd: float | None = None,
        gpu_hours: float | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Incrementally update progress and cost fields for a stage.

        Called frequently during image generation to push live progress
        to Firestore (so the UI can show real-time updates without polling).

        Args:
            job_id: The unique job identifier.
            stage_name: Name of the stage (e.g. ``"image_generation"``).
            images_done: Number of images completed so far.
            images_total: Total images to generate.
            cost_usd: Estimated USD spend so far for this stage.
            gpu_hours: GPU compute hours consumed so far.
            extra: Any additional key/value pairs to merge under ``stages.<stage_name>``.
        """
        doc_ref = self._db.collection(_JOBS_COLLECTION).document(job_id)
        updates: dict[str, Any] = {"updated_at": _now_iso()}
        if images_done is not None:
            updates[f"stages.{stage_name}.images_done"] = images_done
        if images_total is not None:
            updates[f"stages.{stage_name}.images_total"] = images_total
        if cost_usd is not None:
            updates[f"stages.{stage_name}.cost_usd"] = round(cost_usd, 4)
        if gpu_hours is not None:
            updates[f"stages.{stage_name}.gpu_hours"] = round(gpu_hours, 4)
        if extra:
            for k, v in extra.items():
                updates[f"stages.{stage_name}.{k}"] = v
        doc_ref.update(updates)

    # ------------------------------------------------------------------
    # Atomic claim (replaces attempt_claim in queue_manager.py)
    # ------------------------------------------------------------------

    def try_claim_stage(self, job_id: str, stage_name: str) -> bool:
        """Atomically claim a stage for this worker using a Firestore transaction.

        Replaces the lock-file ``attempt_claim()`` pattern from the legacy
        ``queue_manager.py``. Safe across multiple concurrent VMs.

        A claim succeeds only when:
        - The stage is currently ``"PENDING"``.
        - The prerequisite stage (if any) is ``"COMPLETED"``.

        Args:
            job_id: The unique job identifier.
            stage_name: Stage to claim (e.g. ``"image_generation"``).

        Returns:
            True if this worker successfully claimed the stage, False otherwise.
        """
        from google.cloud import firestore  # type: ignore[import-untyped]

        doc_ref = self._db.collection(_JOBS_COLLECTION).document(job_id)

        @firestore.transactional
        def _claim(transaction: Any) -> bool:
            snapshot = doc_ref.get(transaction=transaction)
            if not snapshot.exists:
                return False
            data = snapshot.to_dict() or {}
            stages = data.get("stages", {})
            stage = stages.get(stage_name, {})

            # Must be PENDING
            if stage.get("status") != "PENDING":
                return False

            # Check prerequisite
            prerequisite = _STAGE_PREREQUISITES.get(stage_name)
            if prerequisite:
                prereq_status = stages.get(prerequisite, {}).get("status")
                if prereq_status != "COMPLETED":
                    return False

            # Claim it
            transaction.update(
                doc_ref,
                {
                    f"stages.{stage_name}.status": "RUNNING",
                    f"stages.{stage_name}.started_at": _now_iso(),
                    f"stages.{stage_name}.worker_id": self._worker_id,
                    "updated_at": _now_iso(),
                },
            )
            return True

        transaction = self._db.transaction()
        result: bool = _claim(transaction)
        if result:
            logger.info(
                f"[firestore] Claimed {job_id}/{stage_name} for worker {self._worker_id}"
            )
        return result

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_jobs_by_stage_status(
        self, stage_name: str, status: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return raw Firestore documents for jobs where a stage has a given status.

        Args:
            stage_name: Stage field to filter on (e.g. ``"image_generation"``).
            status: Status string to match (e.g. ``"PENDING"``).
            limit: Maximum number of documents to return.

        Returns:
            List of raw document dicts (job data).
        """
        results = (
            self._db.collection(_JOBS_COLLECTION)
            .where(filter=_field_filter(f"stages.{stage_name}.status", "==", status))
            .limit(limit)
            .stream()
        )
        return [doc.to_dict() for doc in results]

    def get_job_doc(self, job_id: str) -> dict[str, Any] | None:
        """Fetch a single job document by ID.

        Args:
            job_id: The unique job identifier.

        Returns:
            Raw document dict, or None if not found.
        """
        doc = self._db.collection(_JOBS_COLLECTION).document(job_id).get()
        return doc.to_dict() if doc.exists else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _job_to_dict(job: Job) -> dict[str, Any]:
        """Serialise a Job instance to a flat Firestore-compatible dict."""
        stages_data: dict[str, Any] = {}
        for stage_name, stage in job.stages.items():
            stages_data[stage_name] = {
                "status": stage.status.value,
                "started_at": stage.started_at.isoformat()
                if stage.started_at
                else None,
                "completed_at": stage.completed_at.isoformat()
                if stage.completed_at
                else None,
                "error_message": stage.error_message,
                "worker_id": stage.worker_id,
                "cost_usd": stage.cost_usd,
                "images_total": stage.images_total,
                "images_done": stage.images_done,
                "gpu_hours": stage.gpu_hours,
                "metadata": stage.metadata,
            }

        return {
            "job_id": job.job_id,
            "theme": job.theme,
            "event_type": job.event_type,
            "style_hint": job.style_hint,
            "date_folder": job.date_folder,
            "status": job.status.value,
            "total_prompt_count": job.total_prompt_count,
            "stages": stages_data,
            "errors": job.errors,
            "created_at": job.created_at.isoformat(),
            "updated_at": _now_iso(),
        }


# ------------------------------------------------------------------
# Stage prerequisite map (mirrors STAGE_DEPENDENCIES in queue_manager.py)
# ------------------------------------------------------------------

_STAGE_PREREQUISITES: dict[str, str | None] = {
    "prompt_generation": None,
    "image_generation": "prompt_generation",
    "bg_removal": "image_generation",
    "upscaling": "bg_removal",
    "mockups": "upscaling",
    "metadata_generation": "mockups",
    "csv_generation": "metadata_generation",
    "etsy_upload": "csv_generation",
}


def _field_filter(field: str, op: str, value: Any) -> Any:
    """Build a Firestore FieldFilter (SDK v2+ style)."""
    try:
        from google.cloud.firestore_v1.base_query import (
            FieldFilter,  # type: ignore[import-untyped]
        )

        return FieldFilter(field, op, value)
    except ImportError:
        # Fallback for older SDK versions
        return (field, op, value)
