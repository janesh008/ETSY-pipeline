"""Google Drive Service — handles authentication and file uploads to Google Drive.

Exposes a class to upload files (such as generated CLIP prompts or mockups)
to a specific shared Google Drive Folder ID using GCP Service Account credentials
or Application Default Credentials (ADC).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from etsy_pipeline.config.settings import Settings, get_settings
from etsy_pipeline.utils.exceptions import ConfigurationError
from etsy_pipeline.utils.logging import get_logger

logger = get_logger(__name__)

# Required scope for managing files in Google Drive
DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


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
        Resolve user credentials for Google Drive operations using OAuth 2.0.

        Looks for client secrets in the configured path. If an active token.json exists,
        loads it. Otherwise, triggers a local browser sign-in flow once.

        Returns:
            Configured Google Credentials object.

        Raises:
            ConfigurationError: If no client credentials JSON file is configured.
        """
        client_secrets_path = self._settings.google_drive_client_sec_json
        token_path = self._settings.google_drive_token_json

        if not client_secrets_path:
            raise ConfigurationError(
                "GOOGLE_DRIVE_CLIENT_SEC_JSON is not configured. "
                "Download your OAuth client ID credentials from the GCP console and set it in your .env file."
            )

        client_secrets_file = Path(client_secrets_path)
        if not client_secrets_file.exists():
            raise ConfigurationError(
                f"Google Drive Client Secrets file not found at: {client_secrets_file.resolve()}. "
                f"Please download your credentials.json file and place it there."
            )

        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first time.
        token_file = Path(token_path)
        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(token_file), DRIVE_SCOPES
                )
                logger.debug(
                    f"Loaded existing GDrive OAuth token session from: {token_file}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load existing token file: {e}. Re-authenticating..."
                )

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("GDrive access token expired. Refreshing token...")
                try:
                    creds.refresh(Request())
                    # Save refreshed token
                    token_file.parent.mkdir(parents=True, exist_ok=True)
                    token_file.write_text(creds.to_json())
                    logger.debug("GDrive access token refreshed and saved.")
                    return creds
                except Exception as e:
                    logger.warning(
                        f"Failed to refresh GDrive access token: {e}. Restarting login flow."
                    )

            logger.info(
                "No active GDrive OAuth session. Triggering browser login flow..."
            )
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(client_secrets_file),
                    scopes=DRIVE_SCOPES,
                )
                creds = flow.run_local_server(port=0)

                # Save the credentials for the next run
                token_file.parent.mkdir(parents=True, exist_ok=True)
                token_file.write_text(creds.to_json())
                logger.info(f"GDrive OAuth session saved to: {token_file}")
            except Exception as e:
                raise RuntimeError(
                    f"Failed to run OAuth 2.0 InstalledAppFlow: {e}. "
                    f"Make sure you run this script in an environment where a web browser can open."
                ) from e

        return creds

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
            results = service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get("files", [])

            if files:
                folder_id = files[0]["id"]
                logger.debug(
                    f"Found existing date subfolder '{folder_name}' (ID: {folder_id})"
                )
                return str(folder_id)

            # Create the date subfolder if not found
            logger.info(
                f"Creating new date subfolder '{folder_name}' under parent '{parent_id}'"
            )
            file_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            folder = service.files().create(body=file_metadata, fields="id").execute()
            return str(folder.get("id"))

        except Exception as e:
            logger.error(
                f"Failed to check/create date subfolder '{folder_name}' on Drive: {e}"
            )
            # Fallback to the main parent folder if subfolder creation fails
            logger.warning(
                f"Falling back to upload directly to parent folder '{parent_id}'"
            )
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

    def upload_folder(
        self,
        local_dir: Path | str,
        folder_id: str | None = None,
        remote_subfolder_name: str | None = None,
    ) -> list[str]:
        """
        Upload all files in a local directory to Google Drive.

        Optionally creates a subfolder (e.g. theme name) inside the target Drive folder
        to group the uploaded files.

        Args:
            local_dir: Path to the local directory containing files to upload.
            folder_id: Optional ID of the parent folder on Drive (defaults to settings).
            remote_subfolder_name: Optional name for a subfolder to create on Drive to hold the files.

        Returns:
            List of Drive file IDs for the uploaded files.

        Raises:
            NotADirectoryError: If local_dir is not a valid directory.
        """
        local_path = Path(local_dir)
        if not local_path.is_dir():
            raise NotADirectoryError(f"Local path is not a directory: {local_path}")

        main_folder = folder_id or self._settings.google_drive_folder_id
        if not main_folder:
            raise ConfigurationError(
                "No Google Drive folder ID specified. Add GOOGLE_DRIVE_FOLDER_ID to your .env file."
            )

        service = self._get_service()

        # Determine target folder (create subfolder if requested)
        target_folder_id = main_folder
        if remote_subfolder_name:
            # Note: We use the existing parent folder (or date folder) logic
            # For this batch delivery, we create a specific subfolder.
            date_folder_id = self._get_or_create_date_folder(service, main_folder)

            logger.info(
                f"Creating/getting theme subfolder '{remote_subfolder_name}' in Drive"
            )
            query = (
                f"name = '{remote_subfolder_name}' and "
                f"'{date_folder_id}' in parents and "
                f"mimeType = 'application/vnd.google-apps.folder' and "
                f"trashed = false"
            )
            try:
                results = (
                    service.files().list(q=query, fields="files(id, name)").execute()
                )
                files = results.get("files", [])
                if files:
                    target_folder_id = files[0]["id"]
                else:
                    file_metadata = {
                        "name": remote_subfolder_name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [date_folder_id],
                    }
                    folder = (
                        service.files()
                        .create(body=file_metadata, fields="id")
                        .execute()
                    )
                    target_folder_id = folder.get("id")
            except Exception as e:
                logger.error(
                    f"Failed to create subfolder '{remote_subfolder_name}': {e}. Using date folder."
                )
                target_folder_id = date_folder_id
        else:
            target_folder_id = self._get_or_create_date_folder(service, main_folder)

        uploaded_ids = []
        # Upload all files in the directory
        for file_path in sorted(local_path.iterdir()):
            if not file_path.is_file():
                continue

            try:
                file_id = self.upload_file(
                    local_path=file_path, folder_id=target_folder_id
                )
                uploaded_ids.append(file_id)
            except Exception as e:
                logger.error(f"Failed to upload {file_path.name} in batch: {e}")

        logger.info(
            f"Batch uploaded {len(uploaded_ids)} files from {local_path.name} to Drive."
        )
        return uploaded_ids

    def _get_or_create_folder_by_path(
        self, parent_id: str, path_parts: list[str]
    ) -> str:
        """Find or recursively create a nested folder path under a parent folder ID on Drive.

        Args:
            parent_id: Google Drive folder ID of the root directory.
            path_parts: List of folder names representing the path (e.g. ['Clipart', 'main_data', '2026-07-21', 'Iron_man']).

        Returns:
            The folder ID of the leaf subfolder.
        """
        service = self._get_service()
        current_parent = parent_id

        for part in path_parts:
            # Query for an existing folder with the given name under the current parent
            query = (
                f"name = '{part}' and "
                f"'{current_parent}' in parents and "
                f"mimeType = 'application/vnd.google-apps.folder' and "
                f"trashed = false"
            )
            try:
                results = (
                    service.files().list(q=query, fields="files(id, name)").execute()
                )
                files = results.get("files", [])
                if files:
                    current_parent = files[0]["id"]
                    logger.debug(
                        f"Found existing Drive folder '{part}' (ID: {current_parent})"
                    )
                else:
                    # Create the folder if not found
                    logger.info(
                        f"Creating Drive folder '{part}' under parent '{current_parent}'"
                    )
                    file_metadata = {
                        "name": part,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [current_parent],
                    }
                    folder = (
                        service.files()
                        .create(body=file_metadata, fields="id")
                        .execute()
                    )
                    current_parent = folder.get("id")
            except Exception as e:
                logger.error(
                    f"Failed to resolve/create Drive folder '{part}' under parent '{current_parent}': {e}"
                )
                raise RuntimeError(
                    f"Google Drive folder path resolution failed: {e}"
                ) from e

        return current_parent

    def upload_folder_to_path(
        self,
        local_dir: Path | str,
        parent_id: str,
        path_parts: list[str],
    ) -> list[str]:
        """Upload all files in a local directory to a recursively created nested path in Drive.

        Args:
            local_dir: Path to the local directory containing files to upload.
            parent_id: Root folder ID.
            path_parts: List of folder names representing the target path.

        Returns:
            List of Drive file IDs for the uploaded files.
        """
        local_path = Path(local_dir)
        if not local_path.is_dir():
            raise NotADirectoryError(f"Local path is not a directory: {local_path}")

        target_folder_id = self._get_or_create_folder_by_path(parent_id, path_parts)

        uploaded_ids = []
        # Upload all files directly under this folder (flat structure)
        for file_path in sorted(local_path.iterdir()):
            if not file_path.is_file():
                continue

            try:
                # Custom file upload helper that directly uses parent folder_id without date fallback
                file_id = self._upload_file_direct(file_path, target_folder_id)
                uploaded_ids.append(file_id)
            except Exception as e:
                logger.error(
                    f"Failed to upload {file_path.name} in batch to nested path: {e}"
                )

        logger.info(
            f"Batch uploaded {len(uploaded_ids)} files to nested path {path_parts} on Drive."
        )
        return uploaded_ids

    def _upload_file_direct(self, local_path: Path, folder_id: str) -> str:
        """Upload a file directly to a specified parent folder ID, bypassing date subfolders."""
        filename = local_path.name
        service = self._get_service()

        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }

        mimetype = "application/octet-stream"
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
            return str(file_id)
        except Exception as e:
            logger.error(f"Google Drive direct upload failed for {filename}: {e}")
            raise

    def share_folder_publicly(self, folder_id: str) -> str:
        """Make a Google Drive folder readable by anyone with the link.

        Args:
            folder_id: The folder ID to share.

        Returns:
            The public shareable URL.
        """
        service = self._get_service()
        permissions = (
            service.permissions()
            .list(
                fileId=folder_id,
                fields="permissions(id,type,role,allowFileDiscovery)",
                supportsAllDrives=True,
            )
            .execute()
            .get("permissions", [])
        )

        public_permission = next(
            (p for p in permissions if p.get("type") == "anyone"), None
        )

        if public_permission is None:
            service.permissions().create(
                fileId=folder_id,
                body={"type": "anyone", "role": "reader", "allowFileDiscovery": False},
                fields="id,type,role",
                supportsAllDrives=True,
            ).execute()
            logger.info("Folder permission changed to: Anyone with the link (Viewer)")
        else:
            logger.info(
                f"Folder already shared as: {public_permission.get('role', 'reader')}"
            )

        return f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing"

    def get_folder_id_by_path(self, parent_id: str, path_parts: list[str]) -> str:
        """Lookup or create a folder's ID relative to a parent folder by walking the path parts.

        Args:
            parent_id: The starting parent folder ID.
            path_parts: List of directory names to resolve.

        Returns:
            The ID of the final nested folder.
        """
        service = self._get_service()
        current_parent_id = parent_id

        for part in path_parts:
            escaped_name = part.replace("\\", "\\\\").replace("'", "\\'")
            query = (
                f"name = '{escaped_name}' and '{current_parent_id}' in parents and "
                "trashed = false and "
                "(mimeType = 'application/vnd.google-apps.folder' or "
                "mimeType = 'application/vnd.google-apps.shortcut')"
            )
            response = (
                service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="files(id,name,mimeType,shortcutDetails(targetId,targetMimeType))",
                    pageSize=10,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            matches = response.get("files", [])
            if not matches:
                # Create the folder if it does not exist
                folder_metadata = {
                    "name": part,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [current_parent_id],
                }
                new_folder = (
                    service.files()
                    .create(body=folder_metadata, fields="id", supportsAllDrives=True)
                    .execute()
                )
                current_parent_id = new_folder["id"]
            else:
                item = matches[0]
                if item["mimeType"] == "application/vnd.google-apps.shortcut":
                    shortcut = item.get("shortcutDetails", {})
                    if (
                        shortcut.get("targetMimeType")
                        != "application/vnd.google-apps.folder"
                    ):
                        raise ValueError(f"Drive shortcut is not a folder: {part}")
                    current_parent_id = shortcut["targetId"]
                else:
                    current_parent_id = item["id"]

        return current_parent_id
