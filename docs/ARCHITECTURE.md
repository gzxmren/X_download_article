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

## 3. Key Components

### 3.1 `src/main.py` (Controller)
*   **Role**: Orchestrates the workflow.
*   **Logic**:
    1.  Parses CLI arguments.
    2.  Initializes the Browser Context (injecting Cookies).
    3.  Iterates through URLs.
    4.  Skips URLs found in `HistoryManager`.
    5.  Delegates processing to `XDownloader`.
    6.  Triggers `IndexGenerator` upon completion.

### 3.2 `src/extractor.py` (Business Logic)
*   **Role**: The "Brain" that understands X's DOM.
*   **Features**:
    *   **Metadata Strategy**: Uses a waterfall strategy to find the Title/Topic:
        1.  Parse `<title>` tag (regex for `Author: "Topic"` pattern).
        2.  Fallback to `tweetText` div content.
    *   **High-Fidelity Cleaning**: Instead of extracting text, it clones the DOM, strips `<script>`/`<iframe>`/Navbars, and wraps the `<article>` in a centered container with original Twitter fonts/CSS preserved.

### 3.3 `src/indexer.py` (Presentation)
*   **Role**: Generates the knowledge base.
*   **Logic**: Scans the `output/` directory for `meta.json` files and rebuilds a static `index.html` file using a Tailwind CSS template. This ensures the index is always in sync with the file system.

### 3.4 `src/history.py` (Persistence)
*   **Role**: Deduplication.
*   **Implementation**: Maintains a simple file-based set (`downloaded_history.txt`) of processed URLs.

## 4. Data Flow

1.  **Input**: User provides `urls.txt` and `cookies.txt`.
2.  **Auth**: Cookies are loaded via `utils.load_cookies` (supports Netscape/JSON).
3.  **Processing**:
    *   Page loads -> Lazy loading triggered via scrolling.
    *   `XArticleExtractor` identifies metadata (Author, Date, Topic).
    *   Folder created: `output/{Author}_{Topic}_{Date}`.
    *   **Images**: Downloaded to `assets/`, HTML `src` attributes rewritten to relative paths.
    *   **HTML**: DOM snapshot saved with "Style Injection".
    *   **Markdown**: (Optional) Converted via `markdownify`.
4.  **Metadata**: `meta.json` written to folder.
5.  **Finalization**: Global `index.html` updated.

## 5. Future Roadmap
*   **PDF Generation**: Use Playwright's `page.pdf()` feature to render the cleaned HTML into PDF.
*   **Video Support**: Intercept X's HLS/m3u8 network requests to download video streams using `ffmpeg`.