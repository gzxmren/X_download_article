# Changelog

## [Unreleased]

## [1.8.0] - 2026-01-29
### Added
- **Helper CLI**: Introduced `src/helper.py`, a dedicated tool for managing the download database.
    - `sync`: Scans `output/` directory to rebuild the `records.csv` database from existing files (useful for backups/migration).
    - `stats`: Displays statistics on total, successful, and failed downloads.
    - `export`: Exports all downloaded URLs to a text file for easy migration to other machines.
- **Record Manager**: Implemented `src/record_manager.py` to replace the old text-based history system with a structured CSV database (`output/records.csv`).
    - Tracks comprehensive metadata: URL, Title, Author, Date, Local Path, Status, Failure Reason, Timestamp.
    - Implements "Upsert" logic: Prioritizes successful downloads over failures to prevent data loss.

### Changed
- **Architecture**: Merged `HistoryManager` into `RecordManager`. Deprecated `src/history.py` and `logs/downloaded_history.txt`.
- **Logic**: The application now uses `records.csv` as the single source of truth for "Resume/Skip" functionality.

## [1.7.1] - 2026-01-29
### Fixed
- **Image Download Failures**: Resolved frequent "Failed to download image" errors caused by anti-hotlinking protections.
    - Added `Referer` and `Accept` headers to mimic legitimate browser requests.
    - Implemented robust retry logic (3 retries with exponential backoff) using `tenacity` for unstable connections.
    - Increased image download timeout from 10s to 15s.
    - Improved error logging to capture specific exceptions after all retries fail.

## [1.7.0] - 2026-01-27
### Added
- **PDF Export**: Generate A4 PDF documents from downloaded articles using Playwright's printing engine (`--pdf` flag).
- **EPUB Export**: Create offline-ready EPUB e-books with embedded images (`--epub` flag), perfect for e-readers.
- **High-Fidelity Styles**: Improved the Jinja2 template engine to automatically inject original Twitter CSS styles into local HTML copies, ensuring 1:1 visual fidelity.

## [1.6.0] - 2026-01-27
### Added
- **Configuration Management**: Introduced `.env` support via `src/config.py`. Centralized all settings (Timeouts, CSS Selectors, User-Agent) to allow easy updates without code changes.
- **Templating Engine**: Integrated `Jinja2` to separate HTML presentation from Python logic. Added `src/templates/` with `article.html` and `index.html`.
- **Pagination**: The Global Index (`index.html`) now supports pagination. Default is 20 articles per page, configurable via `ITEMS_PER_PAGE` in `.env`.

## [1.5.0] - 2026-01-27
### Added
- **Structured Logging**: Introduced `logs/latest_run.jsonl`, a machine-readable JSON log file for automated analysis and dashboarding.
- **Rich Failure Report**: Upgraded failure reporting to `output/failures.json`. It now includes detailed error messages, timestamps, and retry counts, providing actionable insights into why downloads failed.

## [1.4.0] - 2026-01-27
### Added
- **Parallel Downloading**: Implemented multi-threaded image downloading using `requests` and `ThreadPoolExecutor` (8 workers), significantly boosting speed for image-heavy threads.
- **Robust Error Handling**: Integrated `tenacity` library for automatic retries (up to 3 times with exponential backoff) on network failures.
- **Failure Reporting**: Generates a `failures.txt` report listing any URLs that failed to download after all retries.
- **Documentation**: Added `docs/TECHNICAL_DESIGN.md` (architecture details) and `docs/ROADMAP.md` (future plans).

## [1.3.0] - 2026-01-27
### Added
- **Tools**: Added `src/clean_urls.py` for removing duplicate URLs from input files.
- **Tools**: Added `src/regenerate_index.py` for rebuilding `index.html` instantly without re-downloading.
- **Sorting**: `index.html` now sorts articles based on the order defined in `urls.txt` (if provided).

### Fixed
- **Localization**: Fixed an issue where X automatically translated titles/content to Chinese based on cookies. The tool now filters out language preferences to ensure original content is saved.
- **Input Parsing**: Fixed a bug where commented URLs with leading whitespace were not correctly ignored.

## [1.2.0] - 2025-01-27
### Added
- **Global Index**: Automatically generates `index.html` to visualize all downloaded articles.
- **Resumable Downloads**: Added `HistoryManager` to skip already downloaded URLs.
- **Smart Naming**: Folders and files are now named `Author_Topic_Date` for better sorting.
- **High-Fidelity HTML**: Now preserves original Twitter styles (CSS/Fonts) instead of bare-bones HTML.
- **Logging**: Comprehensive logging to `logs/` directory.

### Changed
- **Architecture**: Refactored monolithic script into modular components (`extractor`, `downloader`, `utils`).
- **Markdown**: Changed to Opt-In (`--markdown` flag required). Default is HTML only.
- **Title Extraction**: Improved regex to handle localized (Chinese/English) X titles correctly.

## [1.1.0] - 2025-01-27
### Added
- Batch download support via `urls.txt`.
- Netscape cookie format support.
- CLI arguments for scroll count and timeout.

## [1.0.0] - 2025-01-27
### Initial Release
- Basic single URL download.
- Image localization.
- HTML to Markdown conversion.
