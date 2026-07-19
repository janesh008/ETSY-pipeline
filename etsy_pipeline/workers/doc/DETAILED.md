# Code Details — `workers`

## Code Behavior
This subpackage contains:
*   [📄 prompt_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/prompt_worker.py) — Stage 1 worker.
*   [📄 prompt_worker_config.py](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/prompt_worker_config.py) — Configuration and templates.

### `PromptWorker` Class Flow
1.  **Entry (`run(job)`):** Checks if prompts are already generated. If not, sets stage status to running, resolves the Gemini client, builds the user prompt, sends it to Gemini, parses the output, validates it, and saves it back to the `Job`.
2.  **Resource Loading (`_load_skill_file()`):** Loads [SKILL.md](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/resources/SKILL.md) at runtime, strips YAML frontmatter, and passes the text as Gemini's `system_instruction`.
3.  **Client Initialization (`_get_client()`):** Supports double auth. If `USE_VERTEX_AI=True`, instantiates the client with `vertexai=True` using GCP Application Default Credentials. Otherwise, initializes with `api_key=google_api_key`.
4.  **Response Parsing (`_parse_response()`):** Uses regex to split Gemini's markdown response into locked sections based on headings (e.g. `## MAIN_CHARACTER`).
5.  **Roster Extraction (`_extract_roster()`):** Parses character name mappings and lists them in `job.character_roster`.
6.  **Validation (`_validate_prompts()`):** Enforces rules (e.g., at least one section must be populated, active sections must have at least 10 prompts, missing sections are added as empty lists).
