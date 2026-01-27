# Project Roadmap & Improvement Proposals

This document outlines suggested improvements and future features for the X Article Downloader project.

## v1.x (Ongoing Optimizations)
*   **Asset Fallback**: Implement placeholder generation or keep original remote links as fallbacks when local image downloading fails.
*   **Structured Logging**: Refine JSON logs and implement cleaner progress tracking (e.g., `tqdm`).
*   **Docker Support**: Provide a `Dockerfile` to standardize the environment and locale settings.

## v2.0 (Major Refactoring: High Concurrency)
*   **Asyncio Re-architecture**: Complete transition from `sync_api` to `async_api` (Asyncio).
*   **Multi-URL Concurrency**: Process multiple URLs simultaneously using browser contexts.
*   **Semaphore Control**: Intelligent concurrency limits to prevent resource exhaustion and account flagging.
*   **Request Context Trace**: Correlation IDs in logs to track interleaved async task outputs.

---

## Technical Details

### 1. Reliability & Error Handling
*   **Retry Mechanism**: (Implemented v1.4.0) Automatic retries using `tenacity`.
*   **Failure Reporting**: (Implemented v1.5.0) Detailed `failures.json`.

### 2. Performance Optimization
*   **Parallel Image Downloads**: (Implemented v1.4.0) ThreadPool for sub-assets.
*   **Concurrency**: (Planned v2.0) Full Asyncio for multi-page processing.

### 3. Configuration Management
*   **External Config**: (Implemented v1.6.0) `.env` and `config.py`.

### 4. Output & Formatting
*   **Templating Engine**: (Implemented v1.6.0) Jinja2 templates.
*   **PDF/EPUB Support**: (Implemented v1.7.0) Native export flags.