# Project Roadmap & Improvement Proposals

This document outlines suggested improvements and future features for the X Article Downloader project.

## 1. Reliability & Error Handling
*   **Retry Mechanism**: Implement automatic retries (e.g., using `tenacity`) for network requests and page loading to handle transient failures.
*   **Failure Reporting**: Generate a summary report (`failures.json` or `failures.txt`) at the end of a batch run, listing failed URLs and error reasons to facilitate targeted re-downloading.

## 2. Performance Optimization
*   **Parallel Image Downloads**: Use a thread pool to download images concurrently within an article, speeding up the processing time per URL.
*   **Asset Fallback**: Implement placeholder generation or keep original remote links as fallbacks when local image downloading fails.

## 3. Configuration Management
*   **External Config**: Move hardcoded constants (CSS selectors, default timeouts, user-agents) to a `config.yaml` or `.env` file. This allows adapting to X platform changes without modifying the source code.

## 4. Deployment & Environment
*   **Docker Support**: Provide a `Dockerfile` and `docker-compose.yml` to standardize the runtime environment, pre-install dependencies, and fix locale settings (avoiding "Chinese title" issues fundamentally).

## 5. Output & Formatting
*   **Templating Engine**: Refactor HTML generation in `extractor.py` and `indexer.py` to use **Jinja2** templates. This separates logic from presentation and allows for easier theming.
*   **PDF/EPUB Support**: Add options to export articles as PDF (via Playwright) or EPUB for better compatibility with e-readers.

## 6. Logging
*   **Structured Logging**: Improve log formatting and separate `DEBUG` logs (like raw HTML dumps) from standard operational logs.
