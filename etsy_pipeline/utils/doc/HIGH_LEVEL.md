# High-Level Responsibilities — `utils`

This subpackage contains shared infrastructure utilities (structured logging and custom exception hierarchies) used across the entire package.

## What it is responsible for
*   Providing clean, uniform exception classes for all 8 pipeline stages.
*   Configuring colored, developer-friendly logs for local terminals and structured JSON logs for GCP Cloud Logging.

## What it is NOT responsible for
*   Managing files, outputs, or configuration keys.
