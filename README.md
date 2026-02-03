# Universal Article Downloader

A high-fidelity, plugin-based content archiving tool powered by Playwright and Python. Designed to capture dynamic web pages (like X.com) exactly as they appear, offline.

## 🚀 Key Features

*   **Plugin Architecture**: Easily extensible to support new platforms (currently supports X.com/Twitter).
*   **High Fidelity**: Captures original HTML, CSS, and Images. No "readability mode" stripping.
*   **Resilient**: Handles network flakes, retries, and scroll-to-load content.
*   **Atomic Data Safety**: Robust database (CSV) handling ensuring no data loss on crashes.
*   **Configurable**: All selectors and behaviors defined in `config.yaml`.
*   **Export Options**: HTML, Markdown, PDF, and EPUB.

## 🛠️ Installation

1.  **Clone and Setup**:
    ```bash
    git clone <repo_url>
    cd X_download_article
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
    ```

2.  **Configuration**:
    The system uses `config.yaml` for settings. You can adjust timeout, scroll count, or CSS selectors there.
    ```yaml
    app:
      headless: true
      timeout: 30
    selectors:
      x_com:
        article: "article"
    ```

## 🏃 Usage

### Basic Download
```bash
# Single URL
python3 src/main.py "https://x.com/username/status/123456789"

# From File
python3 src/main.py input/urls.txt
```

### Options
*   `--pdf`: Generate a PDF version.
*   `--epub`: Generate an EPUB e-book.
*   `--force`: Re-download even if already archived.
*   `--no-headless`: See the browser in action.

## 🧪 Development & Testing

We use `pytest` for quality assurance.

**Run All Tests:**
```bash
./test.sh
```
This will run unit tests, integration tests, and generate a coverage report.

**Project Structure:**
*   `src/plugins/`: Platform-specific logic (e.g., `x_com.py`).
*   `src/main.py`: Core scheduler.
*   `config.yaml`: Central configuration.

## 📝 License
MIT