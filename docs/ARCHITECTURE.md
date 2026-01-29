# Technical Architecture & Design

## 1. System Overview

The **X Article Downloader** is designed as a modular, resilient content archiving system. Unlike simple scrapers, it acts as a **Browser Automation Agent** (using Playwright) to interact with X's complex Single Page Application (SPA) architecture, ensuring high-fidelity capture of dynamic content.

### Core Philosophy
*   **Fidelity**: Prefer rendering original HTML/CSS over reconstructing content manually.
*   **Resilience**: Handle network flakes, timeouts, and anti-bot checks gracefully.
*   **Offline-First**: All assets (images, styles) must be localized. Dependencies on remote servers are removed after download.

## 2. Layered Architecture

The codebase handles complexity through separation of concerns:

```mermaid
graph TD
    User[User Input] --> CLI[main.py / CLI Parser]
    CLI --> Engine[XDownloader Engine]
    
    subgraph Core Services
        Engine -->|1. Navigate & Scroll| Browser[Playwright (Headless)]
        Engine -->|2. Check History| History[HistoryManager]
        Engine -->|3. Extract Content| Extractor[XArticleExtractor]
        Engine -->|4. Save Files| IO[File System]
    end
    
    subgraph Support Modules
        Extractor -->|Clean Filenames| Utils[utils.py]
        Extractor -->|CSS Selectors| Config[XSelector]
        Engine -->|Logging| Logger[logger.py]
    end
    
    IO -->|Generate| Index[IndexGenerator]
    Index --> Output[index.html]
```

### 3. Core Modules

*   **`main.py` (Controller)**:
    *   Entry point for CLI commands.
    *   Orchestrates the browser (Playwright), Extractor, and Exporter.
    *   Manages the download loop and error handling.
*   **`record_manager.py` (Persistence)**:
    *   Manages `output/records.csv`, the central database of all downloaded URLs.
    *   Handles "Upsert" logic (updating records without overwriting success with failure).
    *   Provides "Resume/Skip" functionality by checking if a URL exists in the database.
*   **`helper.py` (Tooling)**:
    *   A standalone CLI for managing the database.
    *   Features: `sync` (rebuild DB from files), `stats` (view counts), `export` (dump URLs).
*   **`extractor.py` (Business Logic)**:
    *   Parses HTML using `BeautifulSoup`.
    *   Sanitizes content (removes scripts, ads).
    *   Extracts metadata (Author, Date, Topic).
    *   Injects original styles via `Jinja2` templates.
*   **`indexer.py` (Presentation)**:
    *   Scans `output/` for `meta.json` files.
    *   Generates a paginated `index.html` dashboard.
*   **`exporter.py` (Export)**:
    *   Handles conversion to PDF (printing) and EPUB (ebook structure).

## Data Flow

1.  **Input**: User provides URL(s) via CLI or `urls.txt`.
2.  **Check**: `RecordManager` checks if URL is already in `records.csv` (status='success').
    *   If yes -> Skip (unless `--force`).
3.  **Fetch**: Playwright loads the page, scrolls to load lazy content.
4.  **Extract**: `XArticleExtractor` parses HTML, cleans it, and extracts metadata.
5.  **Download**:
    *   Images are downloaded in parallel (Thread Pool).
    *   HTML is rewritten to point to local images.
6.  **Save**:
    *   HTML/Markdown saved to `output/Author_Topic_Date/`.
    *   Metadata saved to `meta.json`.
    *   **Record**: `RecordManager` updates `records.csv` with success status.
7.  **Index**: `IndexGenerator` rebuilds `index.html`.

## Directory Structure Design