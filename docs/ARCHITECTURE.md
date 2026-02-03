# Technical Architecture & Design

## 1. System Overview

The **Universal Article Downloader** (formerly X Article Downloader) is a modular, plugin-based content archiving system. It acts as a **Browser Automation Agent** (using Playwright) to capture high-fidelity dynamic content from various platforms.

### Core Philosophy
*   **Fidelity**: Prefer rendering original HTML/CSS over reconstructing content manually.
*   **Resilience**: Handle network flakes, timeouts, and anti-bot checks gracefully.
*   **Extensibility**: Support new platforms via independent plugins without modifying the core engine.
*   **Configuration-Driven**: CSS selectors and behaviors are defined in external YAML files.

## 2. Layered Architecture

The codebase follows a clear separation of concerns using the **Inversion of Control (IoC)** pattern via a Plugin System.

```mermaid
graph TD
    User[User Input] --> CLI[main.py]
    Config[config.yaml] --> Loader[ConfigLoader]
    
    subgraph Core Engine
        CLI --> PluginMgr[PluginManager]
        PluginMgr -->|Selects| Plugin[IPlugin (e.g., XComPlugin)]
        CLI --> Browser[Playwright]
        CLI --> IO[RecordManager (Atomic)]
    end
    
    subgraph Plugin Layer
        Plugin -->|Provides| Extractor[IExtractor]
        Extractor -->|Reads| Loader
        Extractor -->|Parses| HTML[BeautifulSoup]
    end
    
    subgraph Output
        CLI -->|Assets| FS[File System]
        CLI -->|Index| Indexer[IndexGenerator]
        Indexer --> HTML_Out[index.html]
    end
```

### 3. Core Modules

*   **`main.py` (Controller)**:
    *   Orchestrates the download lifecycle: Navigate -> Wait -> Extract -> Download -> Save.
    *   **Agnostic**: Does not contain platform-specific logic (e.g., specific selectors).
    *   Uses `PluginManager` to delegate parsing tasks.
*   **`plugin_manager.py` (Registry)**:
    *   Manages available plugins.
    *   Matches URLs to plugins via `can_handle(url)`.
*   **`src/plugins/` (Extensions)**:
    *   **`x_com.py`**: Implementation for X (Twitter). Encapsulates selectors, metadata extraction, and image finding logic.
    *   **Future**: `bluesky.py`, `medium.py`, etc.
*   **`config.py` (Configuration)**:
    *   Singleton `ConfigLoader` that reads `config.yaml`.
    *   Allows runtime updates to CSS selectors without code changes.
*   **`record_manager.py` (Persistence)**:
    *   **Atomic Writes**: Uses `os.replace` to prevent data corruption.
    *   **Memory Cache**: O(1) lookups for skip logic.

## 4. Key Workflows

### A. Configuration Injection (Scheme A)
Plugins are **self-service**. They directly access the `ConfigLoader` to retrieve their specific settings (e.g., `selectors.x_com`). This keeps the core engine decoupled from plugin-specific configuration needs.

### B. Precise Content Anchoring
To ensure fidelity in complex SPAs (Single Page Applications) like X.com, the system uses an **Anchoring Strategy**:
1.  **ID Extraction**: The plugin extracts the unique Content ID (e.g., Tweet ID) from the source URL.
2.  **ID Matching**: Instead of selecting the first available content block, it scans all candidates (e.g., all `<article>` tags) for a permalink matching that ID.
3.  **Stability**: This ensures that even if ads, context threads, or recommended posts are loaded first, the intended article is correctly identified.

### C. Image Extraction
The responsibility of identifying *which* images to download has been moved from the core engine to the `IExtractor.get_content_images(soup)` interface. This allows plugins to handle complex DOM structures (e.g., background images, lazy-loaded sources) transparently.

## 5. Directory Structure

```text
src/
├── main.py              # Entry point
├── interfaces.py        # Abstract Base Classes (Contracts)
├── plugin_manager.py    # Plugin Registry
├── config.py            # YAML Config Loader
├── plugins/             # Platform implementations
│   ├── __init__.py
│   └── x_com.py
├── record_manager.py    # DB Logic
└── templates/           # Jinja2 Templates
```