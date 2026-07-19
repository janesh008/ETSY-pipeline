# Code Details — `models`

## Code Behavior
This subpackage contains:
*   [📄 job.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/models/job.py)

Defines enums and classes representing job state:

### Enum: `JobStatus`
Defines the overall state of the pipeline: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`.

### Enum: `StageStatus`
Defines the state of an individual stage: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`.

### Class: `StageResult`
Stores results of a specific stage:
*   `status`: StageStatus enum.
*   `started_at` & `completed_at`: Execution timestamps.
*   `error_message`: Traceback or error details if failed.
*   `metadata`: Extra dictionary for ad-hoc stage values.

### Class: `Job`
The primary state object. Exposes:
*   `job_id`: Generated 12-char hex string.
*   `theme`, `event_type` (default `"Normal"`), `style_hint`: Inputs.
*   `prompts`, `generated_images`, `upscaled_images`, `mockups`, `metadata`, `csv_path`: Outputs.
*   `stages`: Dictionary mapping all 8 stages to their `StageResult`.
*   `add_log(msg)`: Appends a timestamped log entry.
*   `add_error(err)`: Records a pipeline error.
*   `get_output_dir(root)`: Returns the output directory path for saving assets.
