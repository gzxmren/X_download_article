import os
import sys
import time
import argparse
import hashlib
import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright, Page
from markdownify import markdownify as md
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Add project root to sys.path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import modules
from src.utils import load_cookies
from src.extractor import XArticleExtractor
from src.logger import logger
from src.indexer import IndexGenerator
from src.config import Config
from src.exporter import Exporter
from src.record_manager import RecordManager

class XDownloader:
    def __init__(self, output_root: str, save_markdown: bool = True, pdf_export: bool = False, epub_export: bool = False):
        self.output_root = output_root
        self.save_markdown = save_markdown
        self.pdf_export = pdf_export
        self.epub_export = epub_export
        self.record_manager = RecordManager(os.path.join(output_root, "records.csv"))

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _download_task(session, url: str, save_path: str) -> bool:
        """
        Executes a single image download task using requests with retries.
        Returns True if successful, raises exception if all retries fail.
        """
        # Use stream=True to avoid loading large files into memory at once
        with session.get(url, stream=True, timeout=15) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _safe_navigate(self, page: Page, url: str, timeout: int):
        """
        Navigates to the URL and waits for the article selector.
        Retries up to 3 times with exponential backoff on failure.
        """
        logger.info(f"Navigating to {url}...")
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        
        logger.info(f"Waiting for content (timeout: {timeout}s)...")
        # Ensure we catch the timeout error to trigger retry
        page.wait_for_selector(Config.Selectors.ARTICLE, timeout=timeout * 1000)
        time.sleep(3) # Wait for hydration

    def process_url(self, page: Page, url: str, scroll_count: int, timeout: int, force: bool = False):
        """
        Returns None if successful/skipped.
        Returns error_dict if failed.
        """
        if not force and self.record_manager.is_downloaded(url):
            logger.info(f"⏭️  Skipping already downloaded: {url}")
            return None

        logger.info(f"Processing URL: {url}")
        try:
            # 1. Navigate with Retry
            try:
                self._safe_navigate(page, url, timeout)
            except Exception as e:
                logger.error(f"❌ Failed to load {url} after retries: {e}")
                self.record_manager.save_record({
                    'url': url,
                    'status': 'failed',
                    'failure_reason': f"Navigation failed: {str(e)}",
                    'source': 'cli_runtime'
                })
                return {
                    "url": url,
                    "error_msg": f"Navigation failed: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                    "retry_attempts": 3 
                }

            # 2. Scroll
            logger.info(f"Scrolling {scroll_count} times...")
            for _ in range(scroll_count):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(1.2)

            # 3. Parse & Extract Metadata
            extractor = XArticleExtractor(page.content(), url)
            if not extractor.is_valid():
                logger.error("No article found in page content.")
                self.record_manager.save_record({
                    'url': url,
                    'status': 'failed',
                    'failure_reason': "No article content found (Extractor invalid)",
                    'source': 'cli_runtime'
                })
                return {
                    "url": url,
                    "error_msg": "No article content found (Extractor invalid)",
                    "timestamp": datetime.now().isoformat(),
                    "retry_attempts": 0
                }

            folder_name = extractor.extract_metadata()
            logger.info(f"Target folder: {folder_name}")

            # DEBUG: If extraction failed effectively (Image_Only), dump HTML
            if "Image_Only" in folder_name:
                logger.warning("Extraction likely failed (Image_Only detected). Saving debug HTML.")
                with open("debug_failed_extraction.html", "w", encoding="utf-8") as f:
                    f.write(page.content())

            # 4. Prepare Directories
            article_dir = os.path.join(self.output_root, folder_name)
            assets_dir = os.path.join(article_dir, "assets")
            os.makedirs(assets_dir, exist_ok=True)

            # 5. Process Content
            # Get high-fidelity HTML skeleton (with original styles)
            raw_html = extractor.get_clean_html()
            final_soup = BeautifulSoup(raw_html, "html.parser")
            
            # --- START PARALLEL IMAGE DOWNLOAD ---
            logger.info("Starting parallel image download...")
            
            # Prepare Requests Session (Copy Cookies from Playwright)
            session = requests.Session()
            # Playwright cookies are list of dicts, requests needs a CookieJar or dict
            pw_cookies = page.context.cookies()
            for cookie in pw_cookies:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            
            # Use User-Agent and other headers to mimic a browser
            session.headers.update({
                "User-Agent": Config.USER_AGENT,
                "Referer": "https://x.com/",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            })

            # Collect tasks
            download_tasks = []
            articles = final_soup.find_all(Config.Selectors.ARTICLE)
            
            for article in articles:
                imgs = article.find_all(Config.Selectors.IMAGES)
                for img in imgs:
                    src = img.get("src")
                    if src and "profile_images" not in src:
                        filename = hashlib.md5(src.encode()).hexdigest() + ".jpg"
                        local_filepath = os.path.join(assets_dir, filename)
                        
                        # Add to task list if not already exists
                        if not os.path.exists(local_filepath):
                            download_tasks.append((img, src, local_filepath))
                        else:
                            # Already exists, just update src
                            img['src'] = os.path.relpath(local_filepath, article_dir)
                            if img.has_attr('srcset'): del img['srcset']

            # Execute tasks in ThreadPool
            if download_tasks:
                with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
                    # Submit all tasks
                    future_to_img = {
                        executor.submit(self._download_task, session, src, path): (img, src, path)
                        for img, src, path in download_tasks
                    }
                    
                    # Process results as they complete
                    for future in future_to_img:
                        img, src, path = future_to_img[future]
                        try:
                            # result() will raise if _download_task failed after retries
                            if future.result():
                                # Success: Update src to local path
                                img['src'] = os.path.relpath(path, article_dir)
                                if img.has_attr('srcset'): del img['srcset']
                        except Exception as exc:
                            # Log the final failure after retries
                            logger.warning(f"Failed to download image after retries: {src}. Error: {exc}")
                            img['data-download-status'] = "failed"
            
            logger.info("Image processing complete.")
            # --- END PARALLEL IMAGE DOWNLOAD ---

            final_markdown = f"# Source: {url}\n\n"
            
            # Re-iterate for cleanup and markdown generation (using updated soup)
            for article in articles:
                # Clean hidden text
                for hidden in article.find_all(class_=lambda x: x and "r-1awozwy" in x and "r-13gxpu9" in x):
                    hidden.decompose()

                # Build Markdown
                if self.save_markdown:
                    final_markdown += f"\n\n---\n\n{md(str(article))}"

            # 6. Save Files
            self._save_html(article_dir, folder_name, str(final_soup))
            if self.save_markdown:
                self._save_markdown(article_dir, folder_name, final_markdown)
            
            # 7. Save Meta.json & Update History
            meta = extractor.get_meta_dict()
            meta['filename_base'] = folder_name
            with open(os.path.join(article_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
            
            # 8. Export (Optional)
            if self.pdf_export:
                pdf_path = os.path.join(article_dir, f"{folder_name}.pdf")
                html_path = os.path.join(article_dir, f"{folder_name}.html")
                Exporter.to_pdf(page, html_path, pdf_path)
                
            if self.epub_export:
                epub_path = os.path.join(article_dir, f"{folder_name}.epub")
                Exporter.to_epub(meta['title'], meta['author'], str(final_soup), assets_dir, epub_path)
            
            # Record Success
            meta['status'] = 'success'
            meta['folder_name'] = folder_name
            self.record_manager.save_record(meta)
            
            logger.info(f"✅ Download completed: {folder_name}")
            return None

        except Exception as e:
            logger.critical(f"Critical error processing {url}: {e}", exc_info=True)
            self.record_manager.save_record({
                'url': url,
                'status': 'failed',
                'failure_reason': f"Critical Exception: {str(e)}",
                'source': 'cli_runtime'
            })
            return {
                "url": url,
                "error_msg": f"Critical Exception: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "retry_attempts": 0
            }

    def _save_html(self, folder: str, title: str, content: str):
        path = os.path.join(folder, f"{title}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved HTML: {path}")

    def _save_markdown(self, folder: str, filename_base: str, content: str):
        path = os.path.join(folder, f"{filename_base}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved Markdown: {path}")

def main():
    parser = argparse.ArgumentParser(description="X Article Downloader (Modularized)")
    parser.add_argument("input", help="URL or file with URLs")
    parser.add_argument("--cookies", "-c", default="input/cookies.txt")
    parser.add_argument("--output", "-o", default="output")
    # Use Config defaults
    parser.add_argument("--headless", action="store_false", dest="headless", help=f"Show browser window (Default: {Config.HEADLESS})")
    parser.add_argument("--scroll", type=int, default=Config.DEFAULT_SCROLL_COUNT)
    parser.add_argument("--timeout", type=int, default=Config.DEFAULT_TIMEOUT)
    parser.add_argument("--markdown", action="store_true", help="Also save as Markdown format (Default: HTML only)")
    parser.add_argument("--pdf", action="store_true", help="Export as PDF (Default: False)")
    parser.add_argument("--epub", action="store_true", help="Export as EPUB (Default: False)")
    parser.add_argument("--force", action="store_true", help="Force redownload even if in history")
    
    # Override default based on Config if needed, but argparse defaults handle it
    parser.set_defaults(headless=Config.HEADLESS, markdown=False)
    args = parser.parse_args()

    # Prepare Inputs
    urls = []
    if os.path.isfile(args.input):
        logger.info(f"Reading URLs from file: {args.input}")
        with open(args.input, 'r') as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    urls.append(stripped.strip('"\'“”'))
    else:
         urls = [args.input.strip().strip('"\'“”')]

    if not urls:
        logger.warning("No URLs to process.")
        return

    # Initialize Engine
    downloader = XDownloader(args.output, args.markdown, args.pdf, args.epub)
    failures = []

    with sync_playwright() as p:
        logger.info(f"Launching browser (Headless: {args.headless})")
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(
            viewport={"width": 1280, "height": 1080},
            user_agent=Config.USER_AGENT # Use Config User-Agent
        )

        # Load Cookies
        cookies = load_cookies(args.cookies)
        if cookies:
            # Filter out 'lang' cookie to prevent X from forcing translated titles/UI
            cookies = [c for c in cookies if c.get('name') != 'lang']
            context.add_cookies(cookies)
            logger.info(f"Loaded {len(cookies)} cookies (filtered language prefs).")
        else:
            logger.warning("Running without cookies (Guest Mode). Content may be limited.")

        page = context.new_page()

        for url in urls:
            error_report = downloader.process_url(page, url, args.scroll, args.timeout, args.force)
            if error_report:
                failures.append(error_report)

        browser.close()
    
    # Generate Index after all tasks
    logger.info("Generating Global Index...")
    indexer = IndexGenerator(args.output, ordered_urls=urls)
    indexer.generate()
    
    # Report Failures
    if failures:
        fail_path = os.path.join(args.output, "failures.json")
        logger.warning(f"⚠️  {len(failures)} URLs failed. Saving report to {fail_path}")
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(failures, f, indent=2, ensure_ascii=False)
    
    logger.info("All tasks completed.")

if __name__ == "__main__":
    main()
