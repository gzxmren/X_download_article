# Changelog

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