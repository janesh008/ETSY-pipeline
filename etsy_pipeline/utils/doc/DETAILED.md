# Code Details — `utils`

## Code Behavior
This subpackage contains:
*   [📄 exceptions.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/utils/exceptions.py)
*   [📄 logging.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/utils/logging.py)

Exposes shared exception definitions and custom log formatting engines:

### `exceptions.py`
Defines the `PipelineError` base exception class (which records stage names and job IDs for traceability). It defines subclass errors for all stages:
*   `PromptGenerationError`, `PromptParsingError`, `PromptValidationError`.
*   `ImageGenerationError`, `BackgroundRemovalError`, `UpscalingError`.
*   `MockupGenerationError`, `MetadataGenerationError`, `CSVGenerationError`, `EtsyUploadError`.
*   `ConfigurationError`, `SkillFileError`.

### `logging.py`
Provides logging utilities:
*   `ColoredFormatter`: Strips complex details and emits cleanly colored terminal messages for local developers.
*   `JsonFormatter`: Converts all log items (including filename, line number, level name, and timestamp) into single-line JSON strings to support GCP Cloud Logging indexing.
*   `setup_logging(level, log_format)`: Sets up the root logger configuration. Must be run only once at startup.
*   `get_logger(name)`: Helper to get a logger.
