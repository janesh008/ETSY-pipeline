# Code Details — `services`

## Code Behavior
This subpackage contains:
*   [📄 google_drive.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/services/google_drive.py) — Google Drive API service.

### `GoogleDriveService`
Provides file upload operations:
*   `_get_credentials()`: Standard Google OAuth resolver. Looks for `gcp_service_account_json` configuration path, sets `GOOGLE_APPLICATION_CREDENTIALS` environment variable to authenticate, or falls back to Application Default Credentials (ADC).
*   `_get_service()`: Instantiates the authorized Google API client build resource for `"drive"`, version `"v3"`.
*   `upload_file(local_path, remote_filename, folder_id)`: Uploads a local file (e.g. text files, images) using a resumable upload session (`MediaFileUpload`). Expects `GOOGLE_DRIVE_FOLDER_ID` setting as folder target.
