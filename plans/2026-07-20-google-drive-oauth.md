# Plan: Google Drive OAuth2 User Authentication

**Date:** 2026-07-20
**Status:** approved
**Related:** [etsy_pipeline/services/doc/HIGH_LEVEL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/services/doc/HIGH_LEVEL.md)

---

## Problem
Service accounts have 0 GB of default storage quota on Google Drive. When they upload files to shared folders, they remain the file owner, triggering a `storageQuotaExceeded` error on personal Gmail accounts. We need to switch to OAuth 2.0 User Authentication so that files are uploaded under the user's personal storage quota.

---

## Clarifying questions & answers
- Q: Will we need to authenticate every time?
  A: No. A `token.json` file is saved locally after the first login, allowing headless automatic runs.

---

## Approach
*   Use `google-auth-oauthlib` and `google-auth-httplib2` to trigger the OAuth 2.0 flow.
*   The script reads `client_secret.json` (downloaded by the user) to initialize the authentication flow.
*   Once authorized in the browser, the credentials are saved locally to `token.json`.
*   Decouple Service Account logic and rely strictly on User OAuth 2.0 for all GDrive operations.

**Alternatives considered:**
- Service Account with Shared Drives — rejected because personal `@gmail.com` accounts do not support Shared Drives.
- Transferring file ownership via API — rejected because Google Drive API does not support transferring ownership from a service account to personal `@gmail.com` accounts.

---

## Scope

**Files/modules touched:**
- `pyproject.toml` — Add `google-auth-oauthlib` and `google-auth-httplib2` dependencies.
- `etsy_pipeline/config/settings.py` — Replace service account settings with `google_drive_client_sec_json` and `google_drive_token_json`.
- `etsy_pipeline/services/google_drive.py` — Implement OAuth 2.0 InstalledAppFlow authentication.
- `.env` & `.env.example` — Update env variable keys.

**Out of scope:**
- Supporting Service Accounts for Google Drive. We will transition fully to OAuth2 User Authentication.

---

## Risks & edge cases
- Token expiration: mitigation — `google.auth.transport.requests.Request` is used to automatically refresh expired tokens using the refresh token stored in `token.json`.
- Missing client secret file: mitigation — Raise a clear `ConfigurationError` explaining how to download the client credentials from the GCP Console.

---

## Steps
1. Add dependencies to `pyproject.toml` and install them.
2. Update settings and env templates.
3. Rewrite credentials resolution in `etsy_pipeline/services/google_drive.py` to use `InstalledAppFlow`.
4. Run validation and verify.

---

## Rollback
- Revert the changes to settings, env, and `google_drive.py` using Git.
