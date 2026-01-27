# Changelog

## [Unreleased]

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
