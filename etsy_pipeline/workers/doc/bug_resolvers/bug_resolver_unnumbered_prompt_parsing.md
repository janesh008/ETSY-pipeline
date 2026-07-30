# Bug Resolver: Unnumbered Prompt Parsing & Dict Truthiness Fallback

## Problem Statement
When running Stage 1 (`image_gen`), `ImageWorker` threw an `ImageGenerationError`:
```
ImageGenerationError: [image_generation] (job=job-57645b0ba054) No prompts found in job — cannot generate images.
```

## Root Cause
1. **Unnumbered Lines in Prompt Files**:
   [PromptWorker._extract_prompts_from_section](file:///d:/Janesh/ETSY/ETSY-pipeline/etsy_pipeline/workers/prompt_worker.py#L462-L503) relied strictly on a regex for numbered line prefixes (`r"^\d+\.\s+"`). When prompt files contained `## SECTION_NAME` headings followed by unnumbered paragraph text (separated by blank lines), zero prompts were extracted.
2. **Dict Truthiness Bug in `create_job`**:
   In [PipelineRunnerService.create_job](file:///d:/Janesh/ETSY/ETSY-pipeline/craftdesk_api/services/pipeline_runner.py#L176-L184), the code checked `if not job.prompts:` to inject fallback prompts. Because `job.prompts` was populated with section keys mapping to empty lists (`{"MAIN_CHARACTER": [], ...}`), `bool(job.prompts)` evaluated to `True`, skipping fallback prompt assignment and leaving `job.total_prompt_count == 0`.

## Fix Applied
1. **`etsy_pipeline/workers/prompt_worker.py`**:
   Updated `_extract_prompts_from_section` to fall back to parsing unnumbered paragraph blocks separated by double newlines (`\n\n`) if no numbered prompt lines are found. Ignored comment lines starting with `(` or `#` or containing inactive section markers.
2. **`craftdesk_api/services/pipeline_runner.py`**:
   Updated `create_job` to check `if job.total_prompt_count == 0:` instead of `if not job.prompts:`.
3. **`tests/test_prompt_worker.py`**:
   Added `test_parses_unnumbered_prompts()` unit test.
