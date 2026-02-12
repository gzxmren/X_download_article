# Changelog

## [2.3.0] - 2026-02-12 (UX & Resilience)

### Features
- **Configurable Pagination**: The number of articles displayed per page in `index.html` is now configurable via `config.yaml` (default: 20). This allows users to adjust the density of the article list based on their preference and performance needs.

### Reliability
- **Robust URL Handling**: Implemented a dedicated `validate_and_fix_url` utility in `src/utils.py`.
    - **Auto-fix**: Automatically corrects common typos like `hhttps://`, `htpp://`, and missing schemes.
    - **Strict Validation**: Uses regex to ensure URLs are valid before attempting to process them, preventing wasted resources on malformed inputs.
    - **Fail-Fast**: Invalid URLs are now skipped immediately with a clear warning, preventing the application from crashing or hanging on bad input.

### Refactoring
- **Code Maintainability**: Moved URL validation logic out of `main.py` into `src/utils.py` to improve code readability and reusability, adhering to the Single Responsibility Principle.

## [2.2.0] - 2026-02-11 (UX & Resilience)

### Reliability
- **Fail Fast Strategy**: Implemented a "Step-up Timeout" mechanism in `safe_navigate`. 
    - **Phase 1 (Probe)**: Attempts a fast connection (10s). If it fails, it catches the error early instead of waiting for the full timeout.
    - **Phase 2 (Retry)**: If the probe fails, retries with the full configured timeout (default 30s) to handle slow but valid connections.
    - This eliminates the frustration of waiting 90s+ for dead links.

### Usability
- **Interactive Skip**: Added `Ctrl+C` handling in the main download loop. Users can now press `Ctrl+C` to instantly skip the current stuck URL and proceed to the next one, without terminating the entire program.

### Refactoring
- **Navigation Logic**: Extracted network navigation logic from `src/main.py` to `src/utils.py` (`safe_navigate`), decoupling business logic from network handling and improving testability.

## [2.1.0] - 2026-02-07 (Security & Reliability)

### Security Hardening
- **SSRF Prevention**: Implemented strict URL validation in `XComPlugin`. Now only allows `http`/`https` schemes and whitelisted domains (x.com, twitter.com) using `urllib.parse`, preventing local file inclusion and intranet scanning.
- **Path Traversal Defense**: Enhanced `sanitize_filename` in `src/utils.py` to filter control characters (0x00-0x1f) and strip leading dots, preventing file system manipulation.
- **CSV Injection Protection**: Updated `RecordManager` to escape fields starting with `=`, `+`, `-`, `@` by prepending a single quote, neutralizing potential Excel macro execution.

### Reliability & Usability
- **Dynamic Waiting**: Replaced hardcoded `time.sleep(3)` in `src/main.py` with `page.wait_for_selector(state="visible")`. This significantly improves speed on fast networks while maintaining stability on slow ones.
- **Interactive Mode**: `src/main.py` now accepts input via stdin if no arguments are provided, allowing users to safely paste complex URLs without worrying about shell escaping.

### Documentation
- Added `docs/SECURITY_REVIEW.md` detailing the security audit findings and fixes.

## [2.0.1] - 2026-02-02 (Resilience & Bug Fixes)

### Fixed
- **Precise ID Anchoring**: Improved `XExtractor` to locate the main tweet using the Tweet ID from the URL. This prevents capturing side-bar ads or context tweets when multiple `<article>` tags are present.
- **Auto-Refresh Loop**: Enhanced HTML cleaning to remove `<meta http-equiv="refresh">` and `on*` event handlers, ensuring saved articles don't redirect or flicker.
- **Indexer Field Compatibility**: Updated `IndexGenerator` to support both `published_date` and `folder_name` fields from the new `ArticleMetadata` model, fixing broken links and missing dates in the dashboard.
- **Stable Filenames**: Included Tweet ID in folder names to ensure uniqueness and prevent link breakage if titles change.

### Lessons Learned
- **Virtual DOM Detachment**: Discovered that excessive scrolling on X.com can remove the focal tweet from the DOM. Recommendation: reduce scroll count if main content is missing.

## [2.0.0] - 2026-02-01 (Architecture Overhaul)

### Added
- **Plugin System**: Introduced `src/plugins/` and `src/plugin_manager.py` to support multiple platforms.
    - Added `XComPlugin` as the default implementation for X (Twitter).
    - Defined `IPlugin` and `IExtractor` interfaces.
- **Configuration Management**: Introduced `config.yaml` and `ConfigLoader`.
    - CSS selectors are now configurable without code changes.
- **Testing Framework**:
    - Added `pytest`, `pytest-mock`, `pytest-cov`.
    - Implemented a "Testing Pyramid": Unit tests for logic, Integration tests with HTML fixtures for parsing.
    - Added `test.sh` for one-click testing and coverage reporting.
- **Atomic Persistence**: `RecordManager` now uses atomic file writes (`os.replace`) to prevent data corruption.

### Changed
- **Refactoring**:
    - `main.py`: Decoupled from specific extractors; now uses `PluginManager`.
    - `extractor.py`: Logic moved to `src/plugins/x_com.py` and file deleted.
    - `config.py`: Rewritten to use `PyYAML` and Singleton pattern.
- **Performance**:
    - `main.py`: Reuse `requests.Session` and `ThreadPoolExecutor` globally across all URLs (HTTP Keep-Alive).
    - `RecordManager`: Loads CSV into memory once at startup for O(1) lookups.

### Fixed
- **Data Safety**: Fixed potential race conditions and file corruption during CSV writing.
- **Type Safety**: Introduced `ArticleMetadata` and `DownloadResult` dataclasses to replace unstructured dictionaries.

## [1.7.0]
- High fidelity single-file HTML export.

## [1.6.0]
- Global Index pagination.

## [1.4.0]
- Parallel image downloading.