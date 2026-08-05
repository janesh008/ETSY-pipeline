"""Main MemoryService facade and prompt context formatter module.

Provides a unified high-level interface for memory capture, recall, filtering,
and formatting memory context for prompt construction.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from etsy_pipeline.config.settings import Settings, get_settings
from etsy_pipeline.memory.base import (
    BaseMemoryProvider,
    MemoryCategory,
    MemoryEntry,
)
from etsy_pipeline.memory.filter import MemoryFilter
from etsy_pipeline.memory.tencent_provider import (
    MockMemoryProvider,
    TencentDBMemoryProvider,
)
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryService:
    """High-level facade service for developer memory operations.

    Applications interact with this class rather than contacting providers directly.
    Exposes capture(), recall(), search(), delete(), health(), and format_for_prompt().
    """

    def __init__(
        self,
        provider: BaseMemoryProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize the MemoryService.

        Args:
            provider: Optional explicit BaseMemoryProvider implementation.
                      If not provided, resolves provider based on settings.
            settings: Optional Settings override.
        """
        self._settings = settings or get_settings()
        self._filter = MemoryFilter()
        self._auto_start_attempted = False

        if provider:
            self._provider = provider
        elif not self._settings.memory_enabled:
            # When feature flag is disabled, use MockMemoryProvider in no-op mode
            logger.info(
                "[memory_service] Memory feature disabled via settings — using MockMemoryProvider"
            )
            self._provider = MockMemoryProvider()
        elif self._settings.memory_provider.lower() == "tencentdb":
            self._provider = TencentDBMemoryProvider(
                gateway_url=self._settings.memory_gateway_url,
                api_key=self._settings.memory_api_key,
                namespace=self._settings.memory_namespace_dev,
                timeout_sec=self._settings.memory_timeout_sec,
            )
            logger.info(
                f"[memory_service] Initialized TencentDBMemoryProvider ({self._settings.memory_gateway_url})"
            )
        else:
            logger.info("[memory_service] Using MockMemoryProvider")
            self._provider = MockMemoryProvider()

    async def _ensure_gateway_running(self) -> None:
        """Verify if the gateway is running; attempt auto-start if offline."""
        if (
            not self._settings.memory_enabled
            or self._settings.memory_provider.lower() != "tencentdb"
        ):
            return
        if self._auto_start_attempted:
            return

        status = await self._provider.health()
        if status.get("status") == "healthy":
            return

        self._auto_start_attempted = True

        # Check if node.exe is already running on the system to avoid port conflicts
        node_running = False
        try:
            # On Windows, tasklist is standard; on Unix, pgrep or ps
            cmd = (
                'tasklist /FI "IMAGENAME eq node.exe"'
                if sys.platform == "win32"
                else "pgrep -f server.ts"
            )
            out = subprocess.check_output(cmd, shell=True, text=True)
            if "node.exe" in out or (sys.platform != "win32" and out.strip()):
                node_running = True
        except Exception:
            pass

        if node_running:
            logger.info(
                "[memory_service] MemoryCore Gateway process is already running but offline. Waiting for it to initialize..."
            )
        else:
            logger.info(
                "[memory_service] MemoryCore Gateway is offline. Attempting background auto-start..."
            )
            self._try_auto_start_gateway()

        # Poll health endpoint every second for up to 20 seconds to allow full initialization
        for i in range(20):
            await asyncio.sleep(1.0)
            status = await self._provider.health()
            if status.get("status") == "healthy":
                logger.info(
                    f"[memory_service] MemoryCore Gateway successfully started and is healthy (boot time: {i + 1}s)"
                )
                return
        logger.warning(
            "[memory_service] MemoryCore Gateway auto-start completed, but server is not responding to health check."
        )

    def _get_gcp_access_token(self) -> tuple[str, str]:
        """Obtain a GCP access token and the project ID using google-auth default credentials with local cache.

        Returns:
            Tuple of (access_token, project_id).
        """
        import json
        import time

        cache_path = (
            Path(self._settings.google_drive_token_json).parent / "gcp_token_cache.json"
        )

        # Try loading cached token first to avoid slow network checks
        if cache_path.exists():
            try:
                with open(cache_path, encoding="utf-8") as f:
                    cache_data = json.load(f)
                expiry = cache_data.get("expiry", 0)
                # Keep a 60-second buffer
                if (
                    time.time() < expiry - 60
                    and cache_data.get("token")
                    and cache_data.get("project_id")
                ):
                    return cache_data["token"], cache_data["project_id"]
            except Exception as e:
                logger.warning(f"[memory_service] Failed to read GCP token cache: {e}")

        try:
            import google.auth
            import google.auth.transport.requests

            logger.info("[memory_service] Fetching fresh GCP ADC token...")
            credentials, project_id = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)

            project_id = project_id or self._settings.gcp_project_id
            token = credentials.token

            # Google access tokens are typically valid for 3600 seconds
            expiry_timestamp = time.time() + 3500

            # Save to cache
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "token": token,
                            "project_id": project_id,
                            "expiry": expiry_timestamp,
                        },
                        f,
                    )
            except Exception as e:
                logger.warning(f"[memory_service] Failed to write GCP token cache: {e}")

            return token, project_id
        except Exception as e:
            logger.warning(f"[memory_service] Failed to fetch GCP ADC credentials: {e}")
            return "", self._settings.gcp_project_id

    def _try_auto_start_gateway(self) -> None:
        """Spawn the MemoryCore Gateway Node.js process in the background."""
        server_dir = Path(self._settings.memory_server_dir)
        memory_core_dir = server_dir / "MemoryCore"

        if (
            not memory_core_dir.exists()
            or not (memory_core_dir / "src/gateway/server.ts").exists()
        ):
            logger.warning(
                f"[memory_service] Auto-start skipped: MemoryCore files not found at '{memory_core_dir}'"
            )
            return

        # Prepare Gateway process environment
        env = os.environ.copy()
        try:
            parsed_url = urllib.parse.urlparse(self._settings.memory_gateway_url)
            host = parsed_url.hostname or "127.0.0.1"
            port = parsed_url.port or 8420
        except Exception:
            host = "127.0.0.1"
            port = 8420

        env["TDAI_GATEWAY_HOST"] = host
        env["TDAI_GATEWAY_PORT"] = str(port)
        if self._settings.memory_api_key:
            env["TDAI_GATEWAY_API_KEY"] = self._settings.memory_api_key

        standalone_config = memory_core_dir / "tdai-gateway.standalone.yaml"
        if standalone_config.exists():
            env["TDAI_GATEWAY_CONFIG"] = str(standalone_config)

        # Configure Vertex AI OpenAI-compatible endpoint using Python's active credentials
        gcp_token, gcp_project = self._get_gcp_access_token()
        location = self._settings.gcp_location or "us-central1"

        if gcp_token and gcp_project:
            logger.info(
                f"[memory_service] Configuring MemoryCore LLM backend via GCP Vertex AI (project={gcp_project}, location={location})"
            )
            env["TDAI_LLM_API_KEY"] = gcp_token
            env["TDAI_LLM_BASE_URL"] = (
                f"https://{location}-aiplatform.googleapis.com/v1/projects/{gcp_project}/locations/{location}/endpoints/openapi"
            )
            model_name = self._settings.gemini_model or "gemini-2.5-flash"
            # Prefix model with google/ as required by Vertex AI OpenAPI endpoint
            if not model_name.startswith("google/"):
                model_name = f"google/{model_name}"
            env["TDAI_LLM_MODEL"] = model_name
        else:
            logger.warning(
                "[memory_service] Google ADC token unavailable. MemoryCore LLM features may fail."
            )

        # Run process hidden/background on Windows
        creationflags = 0
        shell = False
        if sys.platform == "win32":
            creationflags = 0x08000000  # CREATE_NO_WINDOW
            shell = (
                True  # Required to resolve WinError 2 for cmd/bat scripts on Windows
            )

        try:
            logger.info(
                f"[memory_service] Spawning MemoryCore process in background (cwd={memory_core_dir})"
            )

            # Check for npm install requirement
            node_modules = memory_core_dir / "node_modules"
            if not node_modules.exists():
                logger.info(
                    "[memory_service] node_modules not found, installing packages..."
                )
                # Run npm install synchronously since it is a pre-requisite
                subprocess.run(
                    ["npm", "install", "--ignore-scripts"],
                    cwd=str(memory_core_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                    shell=shell,
                    check=True,
                )

            # Start Gateway Node process logging output
            log_path = str(memory_core_dir / "gateway_start.log")
            log_fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            subprocess.Popen(
                ["node", "--import", "tsx", "src/gateway/server.ts"],
                cwd=str(memory_core_dir),
                env=env,
                stdout=log_fd,
                stderr=log_fd,
                creationflags=creationflags,
                shell=shell,
            )
            os.close(log_fd)
            logger.info(
                f"[memory_service] MemoryCore Gateway process spawned successfully. Logs at {log_path}"
            )
        except Exception as exc:
            logger.error(
                f"[memory_service] Failed to auto-start MemoryCore Gateway: {exc}"
            )

    @property
    def is_enabled(self) -> bool:
        """Return True if memory feature is enabled in settings."""
        return self._settings.memory_enabled

    async def capture(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.GENERAL_KNOWLEDGE,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        bypass_filter: bool = False,
    ) -> bool:
        """Filter and capture a developer memory item."""
        if not self._settings.memory_enabled and not bypass_filter:
            return False

        if not bypass_filter and not self._filter.is_worth_remembering(content):
            logger.debug("[memory_service] Memory capture rejected by filter rules")
            return False

        await self._ensure_gateway_running()

        extracted_tags = self._filter.extract_keywords(content)
        all_tags = list(set((tags or []) + extracted_tags))

        return await self._provider.capture(
            content=content,
            category=category,
            tags=all_tags,
            metadata=metadata,
        )

    async def recall(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Recall relevant developer memory items for a query context string."""
        if not self._settings.memory_enabled:
            return []

        await self._ensure_gateway_running()

        try:
            return await self._provider.recall(query, limit=limit)
        except Exception as exc:
            logger.warning(f"[memory_service] Recall failed gracefully: {exc}")
            return []

    async def search(
        self,
        query: str,
        category: MemoryCategory | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search developer memories with optional category filter."""
        if not self._settings.memory_enabled:
            return []

        await self._ensure_gateway_running()

        try:
            return await self._provider.search(query, category=category, limit=limit)
        except Exception as exc:
            logger.warning(f"[memory_service] Search failed gracefully: {exc}")
            return []

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory item by ID."""
        try:
            return await self._provider.delete(memory_id)
        except Exception as exc:
            logger.warning(f"[memory_service] Delete failed gracefully: {exc}")
            return False

    async def health(self) -> dict[str, Any]:
        """Check status of memory provider backend."""
        await self._ensure_gateway_running()
        try:
            return await self._provider.health()
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    @staticmethod
    def format_for_prompt(memories: list[MemoryEntry]) -> str:
        """Format retrieved memories into a clean Markdown block for LLM prompt insertion.

        Args:
            memories: List of MemoryEntry items retrieved via recall().

        Returns:
            Formatted Markdown string ready for prompt injection.
        """
        if not memories:
            return ""

        lines = [
            "### Relevant Developer Context & Past Decisions:",
            "",
        ]
        for idx, mem in enumerate(memories, start=1):
            category_tag = f"[{mem.category.value.upper()}]" if mem.category else ""
            lines.append(f"{idx}. {category_tag} {mem.content.strip()}")

        lines.append("")
        return "\n".join(lines)
