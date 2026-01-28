# Feature Design: Telegram Automated Workflow

**Date:** 2026-01-28  
**Status:** Draft / Planned

## 1. Overview
The goal is to implement a "ChatOps" workflow that allows the user to archive X (Twitter) articles simply by sharing their URLs to a specific Telegram group. The system will automatically detect these URLs, download the content, update the static site index, and provide a daily summary report back to the user via Telegram.

## 2. Core Principles
*   **Loose Coupling:** The "Collector" (Telegram) and the "Downloader" (Core Engine) should be independent, communicating via a simple file-based queue.
*   **Extensibility:** The scheduler should be able to accommodate other input sources in the future.
*   **Observability:** Every step (Fetch -> Download -> Report) must be logged, with a consolidated daily report.

## 3. Architecture Design

We will adopt a **Producer-Consumer** pattern orchestrated by a Scheduler.

### 3.1 Components

1.  **The Source (Producer): `src/telegram_listener.py` (New)**
    *   **Responsibility:** Connects to Telegram API to fetch messages from the specified Group/Channel.
    *   **Logic:**
        *   Read messages since `last_update_id`.
        *   Extract URLs matching `x.com` or `twitter.com`.
        *   Deduplicate against valid history.
        *   Append unique URLs to `input/pending_urls.txt`.
    *   **Output:** Text file with new URLs.

2.  **The Queue: `input/pending_urls.txt`**
    *   **Responsibility:** Acts as a buffer between the async nature of chat and the batch nature of the downloader.

3.  **The Processor (Consumer): `src/main.py` (Existing)**
    *   **Responsibility:** Reads the queue file, executes the download (Headless Browser), and generates static HTML/Markdown.
    *   **Modification:** Minor adjustments to accept a specific input file via CLI args (already supported).

4.  **The Orchestrator: `src/scheduler.py` (New)**
    *   **Responsibility:** The "Main Loop" or Entry Point.
    *   **Modes:**
        *   **daemon:** Runs continuously with a sleep interval (e.g., every 1 hour).
        *   **cron:** Designed to be triggered by system cron.
    *   **Logic:**
        1.  Run `telegram_listener.py`.
        2.  Check if `pending_urls.txt` is not empty.
        3.  If valid jobs exist, run `main.py`.
        4.  Move processed URLs to `logs/processed_history.txt`.
        5.  Accumulate stats for the Daily Report.

5.  **The Reporter: `src/notifier.py` (Existing)**
    *   **Responsibility:** Sends the "Daily Summary" or "Instant Error Alert".

### 3.2 Data Flow

```mermaid
graph TD
    User[User (Mobile/PC)] -->|Share URL| TG[Telegram Group 'X_folder']
    
    subgraph "Server Automation"
        Listener[src/telegram_listener.py] -->|1. Fetch Updates| TG
        Listener -->|2. Extract & Filter| Queue[(input/pending_urls.txt)]
        
        Scheduler[src/scheduler.py] -->|3. Trigger| Listener
        Scheduler -->|4. Detect Work| Queue
        
        Scheduler -->|5. Execute Batch| Main[src/main.py]
        Main -->|6. Download| Web[X.com]
        Main -->|7. Save Content| Output[(output/folders)]
        Main -->|8. Generate Report| JSON[failures.json / run_stats]
        
        Notifier[src/notifier.py] -->|9. Send Daily Summary| TG
    end
```

## 4. Implementation Plan

### Phase 1: Environment & Connectivity
*   [ ] Add `python-telegram-bot` to `requirements.txt`.
*   [ ] Update `.env` with `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
*   [ ] **Create Verification Tool (`src/tools/verify_telegram.py`):**
    *   **Goal:** Ensure the environment is ready before deploying the full listener.
    *   **Checks:**
        1.  **Token Validity:** Call `getMe` to confirm the bot exists and the token is correct.
        2.  **Network Reachability:** Ensure `api.telegram.org` is accessible (checking for proxy needs).
        3.  **Permissions & ID:** Call `getChat` and `sendMessage` to verify read/write access to the target group.
    *   **Feature:** Include an "Echo Mode" to help the user discover the correct `CHAT_ID` by listening to a manual message.

### Phase 2: The Listener
*   [ ] **Create `src/telegram_listener.py`:**
    *   **Extraction Logic:**
        *   Regex: `r"https?://(?:www\.|mobile\.)?(?:twitter\.com|x\.com)/[\w_]+/status/(\d+)"`
        *   Must extract clean URL (remove query parameters like `?s=20`).
    *   **State Persistence:**
        *   File: `data/listener_state.json`
        *   Content: `{"last_update_id": 123456, "last_check_timestamp": "..."}`
        *   Purpose: Prevent reprocessing old messages on restart.
    *   **Deduplication:**
        *   Check against `src/history.py` (global history).
        *   Check against current batch in memory.
        *   Only write *new* and *unprocessed* URLs to `input/pending_urls.txt`.
    *   **Error Handling:** Retry mechanism for Telegram API timeouts.

### Phase 3: The Scheduler & Integration
*   [ ] **Create `src/scheduler.py`:**
    *   **Execution Pattern:** Supports both "Daemon" (loop with sleep) and "One-shot" (for cron).
    *   **Logic Integration:** Use Python `import` to trigger `telegram_listener` and `main.downloader` directly for better error capturing and log consistency.
    *   **Stats Management:**
        *   Log each run's result into a JSONL file: `logs/run_stats.jsonl`.
        *   Track: `timestamp`, `urls_found`, `success_count`, `failure_count`, `error_details`.
    *   **Reporting:**
        *   Aggregate stats daily at a configured time (e.g., 08:00 AM).
        *   Invoke `src/notifier.py` to send the summary report.
    *   **File Cleanup:** After processing, move or archive `pending_urls.txt` to `logs/archived/` to maintain a clean workspace.

## 5. Configuration (Draft)

New settings to be added to `src/config.py` or `.env`:

```python
# Telegram Config
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "..."
TELEGRAM_CHAT_ID = "..." # The group ID to listen to

# Scheduler Config
SCHEDULE_INTERVAL_MINUTES = 60  # How often to check for new messages
DAILY_REPORT_TIME = "08:00"     # When to send the summary
```