# Code Details — `config`

## Code Behavior
This subpackage contains:
*   [📄 settings.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/config/settings.py)

Uses Pydantic's `BaseSettings` to load environment values case-insensitively from the shell or a `.env` file relative to the project root.

### Class: `Settings`
Inherits from `BaseSettings`. Exposes configuration parameters:
*   `use_vertex_ai`: Boolean toggle between Vertex AI (Application Default Credentials) and Google AI Studio API key.
*   `google_api_key`: Direct API key (used when `use_vertex_ai=False`).
*   `gcp_project_id`: Target GCP project ID (used when `use_vertex_ai=True`).
*   `gcp_location`: Region for Vertex AI (e.g. `us-central1`).
*   `gemini_model`: Defaults to `"gemini-2.5-flash"`.
*   `output_root`: Absolute path directory where outputs are written.
*   `skill_file_path`: Resolves to the package resource file [SKILL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/resources/SKILL.md).
*   `metadata_skill_file_path`: Resolves to the package resource file [ETSY-Listing-Master-Prompt.txt](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/resources/ETSY-Listing-Master-Prompt.txt).

### Function: `get_settings()`
A module-level function decorated with `@lru_cache(maxsize=1)` that returns a singleton instance of the `Settings` class, ensuring settings are loaded from disk only once per execution.
