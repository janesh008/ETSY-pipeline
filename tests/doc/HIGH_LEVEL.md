# High-Level Responsibilities — `tests`

This directory houses the automated test suite for verifying the correctness, reliability, and validation rules of the codebase.

## What it is responsible for
*   Providing fast-feedback unit tests to verify prompt parsing, roster parsing, and validation rules without making external API calls.
*   Providing slow-feedback integration tests (marked with `@pytest.mark.integration`) to test real Gemini client connections.

## What it is NOT responsible for
*   Testing code inside the legacy folders `ETSY_main_colab/` or `etsy mockup creator/`.
