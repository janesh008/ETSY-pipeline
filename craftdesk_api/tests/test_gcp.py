"""Tests for craftdesk_api GCP VM router and service."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from craftdesk_api.core.security import create_access_token


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    """Create a user and return Authorization Bearer header dict."""
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "GCP User",
        "email": "gcpuser@example.com",
        "password": "GcpPassword123!",
    })
    user_id = resp.json()["user_id"]
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


class TestGcpConfigEndpoints:

    def test_save_gcp_config_success(self, client, auth_headers) -> None:
        payload = {
            "project_id": "my-gcp-project-123",
            "zone": "us-central1-a",
            "instance_name": "comfy-gpu-instance",
            "service_account_json": '{"type": "service_account", "project_id": "test"}',
            "comfy_ui_port": 8188,
        }
        resp = client.post("/api/v1/gcp/config", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["project_id"] == "my-gcp-project-123"
        assert data["instance_name"] == "comfy-gpu-instance"
        assert data["has_credentials"] is True

    def test_get_gcp_config_success(self, client, auth_headers) -> None:
        payload = {
            "project_id": "my-gcp-project-456",
            "zone": "us-west1-b",
            "instance_name": "gpu-node-1",
            "service_account_json": '{"type": "service_account", "project_id": "test2"}',
            "comfy_ui_port": 8188,
        }
        client.post("/api/v1/gcp/config", json=payload, headers=auth_headers)

        resp = client.get("/api/v1/gcp/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == "my-gcp-project-456"
        assert data["instance_name"] == "gpu-node-1"

    def test_get_gcp_config_not_found(self, client, auth_headers) -> None:
        resp = client.get("/api/v1/gcp/config", headers=auth_headers)
        assert resp.status_code == 404

    def test_unauthenticated_rejected(self, client) -> None:
        resp = client.get("/api/v1/gcp/config")
        assert resp.status_code == 401


class TestGcpVmActions:

    @patch("craftdesk_api.services.gcp_vm.GcpVmService.start_vm")
    def test_start_vm_success(self, mock_start, client, auth_headers) -> None:
        mock_start.return_value = {"status": "DONE"}

        # Save config first
        client.post("/api/v1/gcp/config", json={
            "project_id": "proj",
            "zone": "us-central1-a",
            "instance_name": "gpu-inst",
            "service_account_json": '{"type": "service_account"}',
            "comfy_ui_port": 8188,
        }, headers=auth_headers)

        resp = client.post("/api/v1/gcp/vm/start", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "START"
        assert data["status"] == "STARTING"
        mock_start.assert_called_once()

    @patch("craftdesk_api.services.gcp_vm.GcpVmService.stop_vm")
    def test_stop_vm_success(self, mock_stop, client, auth_headers) -> None:
        mock_stop.return_value = {"status": "DONE"}

        client.post("/api/v1/gcp/config", json={
            "project_id": "proj",
            "zone": "us-central1-a",
            "instance_name": "gpu-inst",
            "service_account_json": '{"type": "service_account"}',
            "comfy_ui_port": 8188,
        }, headers=auth_headers)

        resp = client.post("/api/v1/gcp/vm/stop", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "STOP"
        assert data["status"] == "STOPPING"
        mock_stop.assert_called_once()

    @patch("craftdesk_api.services.gcp_vm.GcpVmService.check_comfy_ui_health")
    @patch("craftdesk_api.services.gcp_vm.GcpVmService.get_vm_details")
    def test_get_vm_status_running_and_ready(self, mock_details, mock_health, client, auth_headers) -> None:
        mock_details.return_value = {
            "status": "RUNNING",
            "external_ip": "34.123.45.67",
        }
        mock_health.return_value = True

        client.post("/api/v1/gcp/config", json={
            "project_id": "proj",
            "zone": "us-central1-a",
            "instance_name": "gpu-inst",
            "service_account_json": '{"type": "service_account"}',
            "comfy_ui_port": 8188,
        }, headers=auth_headers)

        resp = client.get("/api/v1/gcp/vm/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "RUNNING"
        assert data["external_ip"] == "34.123.45.67"
        assert data["comfy_ui_ready"] is True
        assert data["comfy_ui_url"] == "http://34.123.45.67:8188"
