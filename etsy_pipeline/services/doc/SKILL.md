# Coding Skills & Rules — `services`

When working with services:

## 1. Exception Handling & Retries
*   Wrap all remote network calls (HTTP/OAuth) in try-except blocks.
*   Throw clean, descriptive standard python exceptions (like `RuntimeError` or custom exceptions) so callers do not have to inspect low-level socket/client library exceptions directly.

## 2. Directory Permissions Gotcha
*   For Google Drive uploads, the target folder must be shared with the Service Account email address as "Editor".
*   Log clear instructions explaining this permission requirement if uploads return a 403 Forbidden.
