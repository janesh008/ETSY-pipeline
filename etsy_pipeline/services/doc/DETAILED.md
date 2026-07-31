# Code Details — `services`

## Code Behavior
This subpackage contains:
*   [📄 gcs_store.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/services/gcs_store.py) — Google Cloud Storage service wrapper with dual Local & VM guard checks.
*   [📄 google_drive.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/services/google_drive.py) — Google Drive API service.

### `is_gcp_available()`
*   Non-blocking environmental helper that detects if `GOOGLE_APPLICATION_CREDENTIALS`, gcloud CLI ADC credentials, or GCP VM environment flags exist before attempting GCS/Drive network calls.
*   Prevents local non-GCP machines from hanging on `http://169.254.169.254` metadata server timeouts (which previously caused Next.js proxy `ECONNRESET` / `socket hang up` errors).

### `GCSStore`
*   Provides GCS object operations (`upload_file`, `download_file`, `list_objects`, `delete_prefix`).
*   Uses `is_gcp_available()` to safeguard against metadata network hangs in local development.

### `GoogleDriveService`
Provides file upload operations:
*   `_get_credentials()`: Standard Google OAuth resolver. Looks for `gcp_service_account_json` configuration path, sets `GOOGLE_APPLICATION_CREDENTIALS` environment variable to authenticate, or falls back to Application Default Credentials (ADC).
*   `_get_service()`: Instantiates the authorized Google API client build resource for `"drive"`, version `"v3"`.
*   `upload_file(local_path, remote_filename, folder_id)`: Uploads a local file (e.g. text files, images) using a resumable upload session (`MediaFileUpload`). Expects `GOOGLE_DRIVE_FOLDER_ID` setting as folder target.
