# Changelog

## [Unreleased]

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
