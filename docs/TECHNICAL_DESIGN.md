# Technical Design & Implementation Notes

This document records technical decisions, architectural patterns, and proposed optimizations for the X Article Downloader project.

## 1. Image Download Optimization (Implemented v1.4.0)
*   **Model**: Hybrid Parallel (Playwright Main Thread + Requests ThreadPool).
*   **Detail**: High efficiency for asset retrieval without thread-safety risks.

## 2. Global Index & Pagination (Implemented v1.6.0)
*   **Engine**: Jinja2.
*   **Feature**: Static site generation with configurable pagination logic.

## 3. Multi-URL Concurrency Design (Target: v2.0)

### Problem Statement
Currently, URLs are processed sequentially. One URL must complete rendering, scrolling, and metadata extraction before the next begins. This idle time during network waits significantly limits throughput.

### Proposed Architecture: Full Asyncio Transition

To support downloading multiple articles at once, the core engine must be converted to an asynchronous non-blocking model.

#### Core Components:

1.  **Async Playwright (`async_api`)**:
    *   Switch from `sync_playwright` to `async_playwright`.
    *   Methods like `page.goto`, `page.wait_for_selector`, and `page.evaluate` will be awaited.

2.  **Browser Context Isolation**:
    *   Instead of one `context` for all URLs, each download task will create its own `browser.new_context()`.
    *   **Benefit**: Complete isolation of cookies/cache per task if needed, and light-weight resource sharing under one browser process.

3.  **Concurrency Control (Semaphore)**:
    *   Use `asyncio.Semaphore(limit=3)` to cap the number of active browser tabs.
    *   **Reasoning**: Avoid CPU/RAM spikes and reduce the risk of being flagged by X's anti-bot systems.

4.  **Logging Traceability**:
    *   Implement `logging.LoggerAdapter` to inject a unique `request_id` or `short_hash` of the URL into every log record.
    *   **Benefit**: Allows users to filter logs for a specific URL when multiple tasks are printing to the same console/file simultaneously.

#### Implementation Blueprint (Async Pseudocode)

```python
async def process_task(url, semaphore, downloader):
    async with semaphore:
        async with browser.new_context() as context:
            page = await context.new_page()
            # Navigation, Scrolling, Extraction logic (all awaited)
            await downloader.process_url(page, url)

async def main():
    semaphore = asyncio.Semaphore(Config.CONCURRENCY_LIMIT)
    tasks = [process_task(url, semaphore, downloader) for url in urls]
    await asyncio.gather(*tasks)
```

## 4. Single-File High Fidelity (Implemented v1.7.0)
*   **Logic**: Full CSS extraction from source `<style>` tags.
*   **Integration**: Injected into Jinja2 head via `{{ styles | safe }}` to ensure 1:1 visual match for archives.
