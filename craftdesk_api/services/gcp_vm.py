"""CraftDesk API — GCP Compute Engine API wrapper and ComfyUI health poller."""
from __future__ import annotations

import json
from typing import Any

import httpx
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GcpVmService:
    """Manages GCP Compute Engine instances and ComfyUI health verification."""

    @staticmethod
    def _build_compute_client(service_account_json_str: str) -> Any:
        """Parse service account JSON string and build a Compute Engine v1 client."""
        info = json.loads(service_account_json_str)
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/compute"],
        )
        return build("compute", "v1", credentials=credentials, cache_discovery=False)

    @classmethod
    def start_vm(
        cls,
        project_id: str,
        zone: str,
        instance_name: str,
        service_account_json_str: str,
    ) -> dict[str, Any]:
        """Trigger a GCP Compute Engine instance start request.

        Returns the initial operation dictionary from GCP API.
        """
        compute = cls._build_compute_client(service_account_json_str)
        operation = (
            compute.instances()
            .start(project=project_id, zone=zone, instance=instance_name)
            .execute()
        )
        return dict(operation)

    @classmethod
    def stop_vm(
        cls,
        project_id: str,
        zone: str,
        instance_name: str,
        service_account_json_str: str,
    ) -> dict[str, Any]:
        """Trigger a GCP Compute Engine instance stop request.

        Returns the operation dictionary from GCP API.
        """
        compute = cls._build_compute_client(service_account_json_str)
        operation = (
            compute.instances()
            .stop(project=project_id, zone=zone, instance=instance_name)
            .execute()
        )
        return dict(operation)

    @classmethod
    def get_vm_details(
        cls,
        project_id: str,
        zone: str,
        instance_name: str,
        service_account_json_str: str,
    ) -> dict[str, Any]:
        """Fetch instance status and network configuration from GCP API.

        Returns dict containing:
        - status: "RUNNING" | "STOPPED" | "PROVISIONING" | etc.
        - external_ip: str | None
        """
        compute = cls._build_compute_client(service_account_json_str)
        instance_info = (
            compute.instances()
            .get(project=project_id, zone=zone, instance=instance_name)
            .execute()
        )

        status = instance_info.get("status", "UNKNOWN")
        external_ip = None

        network_interfaces = instance_info.get("networkInterfaces", [])
        if network_interfaces:
            access_configs = network_interfaces[0].get("accessConfigs", [])
            if access_configs:
                external_ip = access_configs[0].get("natIP")

        return {
            "status": status,
            "external_ip": external_ip,
        }

    @staticmethod
    async def check_comfy_ui_health(host: str, port: int = 8188) -> bool:
        """Poll the ComfyUI API endpoint at http://<host>:<port>/ to verify readiness.

        Returns True if HTTP status code is 200 within 3.0s timeout.
        """
        if not host:
            return False

        url = f"http://{host}:{port}/"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False
