# Technical Design & Implementation Notes

This document records technical decisions, architectural patterns, and proposed optimizations for the X Article Downloader project.

## 1. Image Download Optimization (Planned)

### Problem Statement
*   **Current State**: Image downloading is sequential (blocking) and tightly coupled with the Playwright execution context.
*   **Issues**: 
    *   Slow processing speed for articles with many images.
    *   Playwright objects (`page`, `request`) are not thread-safe, preventing simple parallelization.
    *   If a download fails, the script warns but leaves the `src` broken or unhandled.

### Proposed Architecture: Hybrid Parallel Model

To achieve high performance without compromising stability, we propose a hybrid model combining **Playwright** (for DOM operations) and **Requests** (for data transfer).

#### Workflow

1.  **Main Thread (Playwright)**
    *   Handles browser automation, page navigation, and DOM parsing.
    *   Extracts all image URLs from the rendered page.
    *   Copies authentication state (Cookies, User-Agent) to a standard Python `requests.Session` object.

2.  **Worker Threads (Requests + ThreadPool)**
    *   A `ThreadPoolExecutor` (e.g., 4-8 workers) handles the actual image downloading using the `requests` library.
    *   **Reasoning**: `requests` is thread-safe and lightweight compared to spinning up multiple browser contexts.

3.  **Fallback Strategy (Graceful Degradation)**
    *   **Success**: Replace the HTML `<img>` `src` attribute with the relative local path (`assets/xxx.jpg`).
    *   **Failure**: 
        *   **Do NOT** clear the `src`. Keep the original remote URL (Hotlinking) so the image can still load if the network permits.
        *   Add a `data-download-status="failed"` attribute to the tag for debugging purposes.

#### Implementation Blueprint (Pseudocode)

```python
import requests
from concurrent.futures import ThreadPoolExecutor

class XDownloader:
    def _download_task(self, session, url, save_path):
        """Executed in worker thread via requests"""
        try:
            resp = session.get(url, timeout=10) 
            resp.raise_for_status()
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            return True
        except Exception:
            return False

    def process_url(self, page, ...):
        # 1. Prepare Session (Sync auth state)
        session = requests.Session()
        # Transfer cookies from Playwright context to Requests session...
        
        # 2. Extract & Plan
        img_tags = soup.find_all('img')
        download_jobs = []
        
        # 3. Parallel Execute
        with ThreadPoolExecutor(max_workers=5) as executor:
            for img in img_tags:
                src = img.get('src')
                local_path = ...
                future = executor.submit(self._download_task, session, src, local_path)
                download_jobs.append((img, future, local_path))
        
        # 4. Resolve & Replace
        for img, future, local_path in download_jobs:
            if future.result(): 
                img['src'] = local_path  # Success: Use local
            else:
                img['data-status'] = "remote_fallback" # Fail: Keep remote
```

### 2. Error Handling & Reliability

*   **Retry Logic**: Critical network operations (Page Navigation, Selector Waiting) are wrapped with `tenacity` decorators using exponential backoff.
*   **Failure Reporting**: Failed tasks are not silent; they are collected and written to a `failures.txt` file at the end of the batch process for easy re-execution.

## 3. Logging System Enhancements

### 3.1 Structured JSON Logs
*   **Goal**: Enable automated analysis and easier debugging.
*   **Implementation**: Add a dedicated FileHandler that outputs logs in JSONL format.
*   **Fields**: `timestamp`, `level`, `module`, `message`, `extra_data` (optional).

### 3.2 Rich Failure Reporting
*   **Goal**: Provide actionable insights on *why* a URL failed, not just *that* it failed.
*   **Implementation**: 
    *   Upgrade `failures.txt` to `failures.json`.
    *   Structure:
        ```json
        [
          {
            "url": "https://x.com/...",
            "error": "TimeoutError: Waited 30s...",
            "timestamp": "2026-01-27T10:00:00",
            "retry_count": 3
          }
        ]
        ```

### 3.3 Request Context (Future)
*   **Goal**: Trace logs belonging to a specific URL processing task in multi-threaded environments.
*   **Implementation**: Use `logging.LoggerAdapter` or context vars to inject a `request_id` into every log entry generated during a URL's processing lifecycle.