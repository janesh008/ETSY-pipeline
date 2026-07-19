"""Google Drive Service — handles authentication and file uploads to Google Drive.

Exposes a class to upload files (such as generated CLIP prompts or mockups)
to a specific shared Google Drive Folder ID using GCP Service Account credentials
or Application Default Credentials (ADC).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from etsy_pipeline.config.settings import Settings, get_settings
from etsy_pipeline.utils.exceptions import ConfigurationError
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)

# Required scope for managing files in Google Drive
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]


class GoogleDriveService:
    """
    Handles authentication and file operations on Google Drive.

    Uses credentials loaded from settings (Service Account JSON or
    Application Default Credentials) to upload files to a target shared folder.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize the Google Drive service client.

        Args:
            settings: Optional app Settings override. Exposes credentials configuration.
        """
        self._settings = settings or get_settings()
        self._service: Any = None

    def _get_credentials(self) -> Any:
        """
        Resolve GCP credentials for Google Drive operations.

        Supports:
        1. Explicit Service Account JSON file path from Settings.
        2. Application Default Credentials (ADC) environment variables.

        Returns:
            Configured Google Credentials object.
        """
        # If a service account JSON is configured, authenticate using that file
        if self._settings.google_drive_service_account_json:
            json_path = Path(self._settings.google_drive_service_account_json)
            if not json_path.exists():
                raise ConfigurationError(
                    f"Google Drive Service Account JSON not found at: {json_path}. Check your .env file."
                )

            logger.debug(f"Loading Drive credentials from Service Account file: {json_path}")
            return service_account.Credentials.from_service_account_file(
                str(json_path),
                scopes=DRIVE_SCOPES,
            )

        # Fallback to Application Default Credentials
        logger.debug("Attempting to load Drive credentials from Application Default Credentials (ADC)")
        try:
            credentials, _ = google.auth.default(scopes=DRIVE_SCOPES)
            return credentials
        except google.auth.exceptions.DefaultCredentialsError as e:
            raise ConfigurationError(
                "Default credentials not found. Run 'gcloud auth application-default login' "
                "or specify GCP_SERVICE_ACCOUNT_JSON in your .env file."
            ) from e

    def _get_service(self) -> Any:
        """
        Get or initialize the Google Drive API client service.

        Returns:
            Authorized Google API discovery Resource client.
        """
        if self._service is not None:
            return self._service

        credentials = self._get_credentials()
        logger.info("Initializing Google Drive API service (v3)")
        self._service = build("drive", "v3", credentials=credentials)
        return self._service

    def _get_or_create_date_folder(self, service: Any, parent_id: str) -> str:
        """
        Check if a folder named with the current date (YYYY-MM-DD) exists, or create it.

        Args:
            service: Google Drive API service resource client.
            parent_id: The main folder ID.

        Returns:
            The ID of the date folder.
        """
        folder_name = datetime.now().strftime("%Y-%m-%d")

        # Search for an existing date folder under the parent folder
        query = (
            f"name = '{folder_name}' and "
            f"'{parent_id}' in parents and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )

        try:
            results = (
                service.files()
                .list(q=query, fields="files(id, name)")
                .execute()
            )
            files = results.get("files", [])

            if files:
                folder_id = files[0]["id"]
                logger.debug(f"Found existing date subfolder '{folder_name}' (ID: {folder_id})")
                return str(folder_id)

            # Create the date subfolder if not found
            logger.info(f"Creating new date subfolder '{folder_name}' under parent '{parent_id}'")
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            folder = (
                service.files()
                .create(body=file_metadata, fields="id")
                .execute()
            )
            return str(folder.get("id"))

        except Exception as e:
            logger.error(f"Failed to check/create date subfolder '{folder_name}' on Drive: {e}")
            # Fallback to the main parent folder if subfolder creation fails
            logger.warning(f"Falling back to upload directly to parent folder '{parent_id}'")
            return parent_id

    def upload_file(
        self,
        local_path: Path,
        remote_filename: str | None = None,
        folder_id: str | None = None,
    ) -> str:
        """
        Upload a local file to a Google Drive folder inside a date-named subfolder.

        Args:
            local_path: Absolute Path to the local file to upload.
            remote_filename: Optional name for the file on Drive (defaults to local basename).
            folder_id: Optional ID of the parent folder. Defaults to the GOOGLE_DRIVE_FOLDER_ID setting.

        Returns:
            The uploaded file ID from Google Drive.

        Raises:
            FileNotFoundError: If the local file does not exist.
            ConfigurationError: If no parent folder ID is configured.
            RuntimeError: If the upload operation fails.
        """
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found for upload: {local_path}")

        main_folder = folder_id or self._settings.google_drive_folder_id
        if not main_folder:
            raise ConfigurationError(
                "No Google Drive folder ID specified. Add GOOGLE_DRIVE_FOLDER_ID to your .env file."
            )

        filename = remote_filename or local_path.name
        service = self._get_service()

        # Get or create date-named subfolder (YYYY-MM-DD) inside the main folder
        target_folder = self._get_or_create_date_folder(service, main_folder)

        logger.info(
            f"Uploading file '{filename}' ({local_path.stat().st_size} bytes) to target Drive folder '{target_folder}'"
        )

        file_metadata = {
            "name": filename,
            "parents": [target_folder],
        }

        # Select standard MIME types based on extension
        mimetype = "text/plain"
        if local_path.suffix == ".csv":
            mimetype = "text/csv"
        elif local_path.suffix in [".png", ".jpg", ".jpeg"]:
            mimetype = f"image/{local_path.suffix[1:]}"

        media = MediaFileUpload(
            str(local_path),
            mimetype=mimetype,
            resumable=True,
        )

        try:
            drive_file = (
                service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id",
                )
                .execute()
            )

            file_id = drive_file.get("id")
            if not file_id:
                raise RuntimeError("Drive API returned response without file ID.")

            logger.info(f"File uploaded successfully. Drive File ID: {file_id}")
            return str(file_id)

        except Exception as e:
            logger.error(f"Google Drive upload failed for {filename}: {e}")
            raise RuntimeError(
                f"Google Drive upload failed. Make sure the folder '{target_folder}' "
                f"is shared with your Service Account email as Editor. Error: {e}"
            ) from e

