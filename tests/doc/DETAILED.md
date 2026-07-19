# Code Details — `tests`

## Code Behavior
This directory contains:
*   [📄 test_prompt_worker.py](file:///d:/Janesh/ETSY/ETSY-pipeline/tests/test_prompt_worker.py) — Unit and integration tests.

### `test_prompt_worker.py`
Exposes the test suite for prompt workers:

#### Fixtures:
*   `sample_gemini_response`: Holds a full mock plain-text Gemini response with locked headings and prompt entries. Used to verify parser correctness.
*   `empty_mock_job` & `valid_mock_job`: Pre-configured jobs used for testing state transitions and validations.

#### Unit Tests:
*   `TestParseResponse`: Verifies that the parser splits the Gemini response correctly, extracts active prompts, records them to the job, and correctly lists inactive sections.
*   `TestValidatePrompts`: Assures validation succeeds when inputs are correct, but throws `PromptValidationError` when active sections are missing or under the 10-prompt floor.
*   `TestBuildUserMessage`: Checks that style overrides, theme parameters, and event variables are correctly integrated into user prompts.

#### Integration Tests:
*   `test_prompt_generation_integration`: Marks with `@pytest.mark.integration`. Instantiates a real `PromptWorker` and triggers a real API call (Vertex AI or Google AI based on `.env`) to verify client authentication and response parsing end-to-end.
