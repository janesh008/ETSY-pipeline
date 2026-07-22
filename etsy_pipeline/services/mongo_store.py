"""MongoDB Job Store — atomic job state persistence backed by MongoDB.

Replaces the Firestore store with a MongoDB-compatible approach,
using `find_one_and_update` for atomic claim operations across VMs.

Responsibility: Read, write, and atomically claim pipeline job state in MongoDB.
"""

from __future__ import annotations

import socket
from datetime import datetime

try:
    from datetime import UTC
except ImportError:
    import datetime as dt

    UTC = dt.UTC
from typing import TYPE_CHECKING, Any

from etsy_pipeline.utils.logging import get_logger

if TYPE_CHECKING:
    from etsy_pipeline.config.settings import Settings
    from etsy_pipeline.models.job import Job

logger = get_logger(__name__)

# MongoDB collection name
_JOBS_COLLECTION = "jobs"


def _now_iso() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


class MongoJobStore:
    """Atomic job state store backed by MongoDB.

    Wraps PyMongo to provide clean read/write/claim operations for pipeline Job documents.
    State mutations use atomic operations (`$set`, `find_one_and_update`) to prevent
    race conditions across multiple worker VMs.

    Usage::

        store = MongoJobStore(settings=get_settings())
        store.upsert_job(job)
        store.update_stage_progress(job_id, "image_generation", images_done=45, cost_usd=1.47)
        pending_jobs = store.list_jobs_by_stage_status("image_generation", "PENDING")
    """

    def __init__(self, settings: Settings) -> None:
        """Initialise the MongoDB client.

        Args:
            settings: Loaded pipeline settings (used for mongo_uri and db name).
        """
        try:
            from pymongo import MongoClient  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "pymongo is not installed. Run: pip install pymongo"
            ) from exc

        self._settings = settings
        self._client: MongoClient[Any] = MongoClient(settings.mongo_uri)
        self._db = self._client[settings.mongo_db_name]
        self._collection = self._db[_JOBS_COLLECTION]

        # Create an index on job_id for faster lookups
        self._collection.create_index("job_id", unique=True)

        self._worker_id = f"{socket.gethostname()}-{id(self)}"

        # Redact password for logging
        safe_uri = (
            settings.mongo_uri.split("@")[-1]
            if "@" in settings.mongo_uri
            else settings.mongo_uri
        )
        logger.info(
            f"[mongo] MongoDB client initialised "
            f"(uri=...{safe_uri[:15]}..., db={settings.mongo_db_name}, worker_id={self._worker_id})"
        )

    # ------------------------------------------------------------------
    # Write / Upsert
    # ------------------------------------------------------------------

    def upsert_job(self, job: Job) -> None:
        """Create or fully overwrite a job document in MongoDB.

        Serialises the entire Job model (including all stage results) into a
        MongoDB document. Idempotent — safe to call multiple times.

        Args:
            job: The Job instance to persist.
        """
        data = self._job_to_dict(job)
        self._collection.update_one(
            {"job_id": job.job_id},
            {"$set": data},
            upsert=True,
        )
        logger.info(f"[mongo] Upserted job {job.job_id} ({job.theme})")

    def update_stage_status(
        self,
        job_id: str,
        stage_name: str,
        status: str,
        *,
        error_message: str | None = None,
        worker_id: str | None = None,
    ) -> None:
        """Update the status of a single stage field in MongoDB.

        Args:
            job_id: The unique job identifier.
            stage_name: Name of the stage (e.g. ``"image_generation"``).
            status: New status string (``"PENDING"``, ``"RUNNING"``, ``"COMPLETED"``, ``"FAILED"``).
            error_message: Optional error string (set when status is ``"FAILED"``).
            worker_id: Identifier of the claiming VM / process.
        """
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

        self._collection.update_one({"job_id": job_id}, {"$set": updates})
        logger.debug(f"[mongo] {job_id}/{stage_name} → {status}")

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
        to MongoDB.

        Args:
            job_id: The unique job identifier.
            stage_name: Name of the stage (e.g. ``"image_generation"``).
            images_done: Number of images completed so far.
            images_total: Total images to generate.
            cost_usd: Estimated USD spend so far for this stage.
            gpu_hours: GPU compute hours consumed so far.
            extra: Any additional key/value pairs to merge under ``stages.<stage_name>``.
        """
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

        self._collection.update_one({"job_id": job_id}, {"$set": updates})

    # ------------------------------------------------------------------
    # Atomic claim
    # ------------------------------------------------------------------

    def try_claim_stage(self, job_id: str, stage_name: str) -> bool:
        """Atomically claim a stage for this worker using MongoDB find_one_and_update.

        Safe across multiple concurrent VMs.

        A claim succeeds only when:
        - The stage is currently ``"PENDING"``.
        - The prerequisite stage (if any) is ``"COMPLETED"``.

        Args:
            job_id: The unique job identifier.
            stage_name: Stage to claim (e.g. ``"image_generation"``).

        Returns:
            True if this worker successfully claimed the stage, False otherwise.
        """
        from pymongo import ReturnDocument  # type: ignore[import-untyped]

        # Build the atomic match query (allows claiming both PENDING and FAILED stages)
        query: dict[str, Any] = {
            "job_id": job_id,
            f"stages.{stage_name}.status": {"$in": ["PENDING", "FAILED"]},
        }

        # Check prerequisite in the atomic query if it exists
        prerequisite = _STAGE_PREREQUISITES.get(stage_name)
        if prerequisite:
            query[f"stages.{prerequisite}.status"] = "COMPLETED"

        # The updates to apply if the document matches the query
        updates = {
            "$set": {
                f"stages.{stage_name}.status": "RUNNING",
                f"stages.{stage_name}.started_at": _now_iso(),
                f"stages.{stage_name}.worker_id": self._worker_id,
                "updated_at": _now_iso(),
            }
        }

        # Atomically find and update. If it returns a document, we claimed it.
        result = self._collection.find_one_and_update(
            query, updates, return_document=ReturnDocument.AFTER
        )

        if result:
            logger.info(
                f"[mongo] Claimed {job_id}/{stage_name} for worker {self._worker_id}"
            )
            return True

        return False

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_jobs_by_stage_status(
        self, stage_name: str, status: str | list[str], limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return raw MongoDB documents for jobs where a stage has a given status (or list of statuses).

        Args:
            stage_name: Stage field to filter on (e.g. ``"image_generation"``).
            status: Status string or list of status strings to match (e.g. ``"PENDING"`` or ``["PENDING", "FAILED"]``).
            limit: Maximum number of documents to return.

        Returns:
            List of raw document dicts (job data).
        """
        status_filter = {"$in": status} if isinstance(status, list) else status
        cursor = self._collection.find(
            {f"stages.{stage_name}.status": status_filter}
        ).limit(limit)

        # Convert cursor to list and remove MongoDB's internal _id to match dict shape
        results = []
        for doc in cursor:
            doc.pop("_id", None)
            results.append(doc)

        return results

    def get_job_doc(self, job_id: str) -> dict[str, Any] | None:
        """Fetch a single job document by ID.

        Args:
            job_id: The unique job identifier.

        Returns:
            Raw document dict, or None if not found.
        """
        doc = self._collection.find_one({"job_id": job_id})
        if doc:
            doc.pop("_id", None)
        return doc

    def get_job(self, job_id: str) -> Job | None:
        """Fetch a single Job model instance by ID.

        Args:
            job_id: The unique job identifier.

        Returns:
            Populated Job object, or None if not found.
        """
        doc = self.get_job_doc(job_id)
        if not doc:
            return None
        from etsy_pipeline.models.job import Job

        return Job.model_validate(doc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _job_to_dict(job: Job) -> dict[str, Any]:
        """Serialise a Job instance to a flat MongoDB-compatible dict."""
        data = job.model_dump(mode="json")
        data["updated_at"] = _now_iso()
        return data


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
