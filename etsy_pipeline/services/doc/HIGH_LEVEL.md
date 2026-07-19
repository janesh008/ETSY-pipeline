# High-Level Responsibilities — `services`

This subpackage contains third-party API service integrations and client wrappers that are utilized by workers or CLI scripts.

## What it is responsible for
*   Providing clean interfaces for interacting with Google Drive (like `GoogleDriveService`).
*   Configuring and managing API credentials for external storage/drive systems.

## What it is NOT responsible for
*   Any pipeline orchestration or parsing logic.
