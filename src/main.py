import os
import sys
import time
import argparse
import hashlib
import json
import requests
from datetime import datetime
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
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
from src.logger import logger
from src.indexer import IndexGenerator
from src.config import Config
from src.exporter import Exporter
from src.record_manager import RecordManager
from src.models import ArticleMetadata, DownloadResult
from src.plugin_manager import PluginManager

class XDownloader:
    def __init__(self, output_root: str, save_markdown: bool = True, pdf_export: bool = False, epub_export: bool = False):
        self.output_root = output_root
        self.save_markdown = save_markdown
        self.pdf_export = pdf_export
        self.epub_export = epub_export
        self.record_manager = RecordManager(os.path.join(output_root, "records.csv"))
        self.plugin_manager = PluginManager()
        
        # Performance: Global resource pool
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": Config.USER_AGENT,
            "Referer": "https://x.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)

    def close(self):
        """Cleanly shutdown global resources."""
        self.executor.shutdown(wait=True)
        self.session.close()
        logger.info("Downloader resources released.")

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _download_task(session: requests.Session, url: str, save_path: str) -> bool:
        """Executes a single image download task."""
        with session.get(url, stream=True, timeout=15) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _safe_navigate(self, page: Page, url: str, timeout: int, wait_selector: str):
        """Navigates with retry logic."""
        logger.info(f"Navigating to {url}...")
        try:
            # Use 'domcontentloaded' - 'networkidle' is too flaky on X.com due to constant polling
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            # Ensure the specific content is visible (this is the key check)
            page.wait_for_selector(wait_selector, state="visible", timeout=timeout * 1000)
        except Exception as e:
            logger.warning(f"Navigation attempt failed for {url}: {e}")
            raise e

    def process_url(self, page: Page, url: str, scroll_count: int, timeout: int, force: bool = False) -> Optional[DownloadResult]:
        """
        Processes a single URL. Returns DownloadResult if error occurred, else None.
        """
        if not force and self.record_manager.is_downloaded(url):
            logger.info(f"⏭️  Skipping already downloaded: {url}")
            return None

        logger.info(f"Processing URL: {url}")
        result = DownloadResult(url=url, success=False)
        
        try:
            # 0. Get Plugin
            try:
                plugin = self.plugin_manager.get_plugin(url)
            except ValueError as e:
                logger.error(str(e))
                result.error_msg = str(e)
                return result

            # 1. Navigate
            try:
                self._safe_navigate(page, url, timeout, plugin.get_wait_selector())
            except Exception as e:
                # Check for specific network/timeout indicators
                is_timeout = isinstance(e, PlaywrightTimeoutError) or "Timeout" in str(e) or "timeout" in str(e)
                
                if is_timeout:
                    logger.warning(f"⚠️  Timeout detected. This might be due to a slow network or the site blocking requests.")
                    logger.error(f"❌ Failed to load {url} (Network/Timeout): {e}")
                    meta = ArticleMetadata(url=url, status='failed', failure_reason=f"Network Timeout: {str(e)}")
                else:
                    logger.error(f"❌ Failed to load {url}: {e}")
                    meta = ArticleMetadata(url=url, status='failed', failure_reason=f"Navigation: {str(e)}")

                self.record_manager.save_record(meta.to_dict())
                result.error_msg = str(e)
                return result

            # 2. Scroll
            logger.info(f"Scrolling {scroll_count} times...")
            for _ in range(scroll_count):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(1.2)

            # 3. Extract
            extractor = plugin.get_extractor(page.content(), url)
            if not extractor.is_valid():
                logger.error("No article found.")
                meta = ArticleMetadata(url=url, status='failed', failure_reason="No article content found")
                self.record_manager.save_record(meta.to_dict())
                result.error_msg = "No article found"
                return result

            # 4. Meta & Folders
            article_meta = extractor.extract_metadata_obj()
            logger.info(f"Target folder: {article_meta.folder_name}")

            article_dir = os.path.join(self.output_root, article_meta.folder_name)
            assets_dir = os.path.join(article_dir, "assets")
            os.makedirs(assets_dir, exist_ok=True)

            # 5. Parallel Image Processing
            # Sync cookies
            pw_cookies = page.context.cookies()
            for cookie in pw_cookies:
                self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

            raw_html = extractor.get_clean_html()
            final_soup = BeautifulSoup(raw_html, "html.parser")
            
            # Delegate image finding to plugin
            images = extractor.get_content_images(final_soup)
            
            download_tasks = []
            for img, src in images:
                filename = hashlib.md5(src.encode()).hexdigest() + ".jpg"
                local_filepath = os.path.join(assets_dir, filename)
                
                if not os.path.exists(local_filepath):
                    download_tasks.append((img, src, local_filepath))
                else:
                    img['src'] = os.path.relpath(local_filepath, article_dir)
                    if img.has_attr('srcset'): del img['srcset']

            if download_tasks:
                logger.info(f"Downloading {len(download_tasks)} images...")
                futures = {
                    self.executor.submit(self._download_task, self.session, src, path): (img, src, path)
                    for img, src, path in download_tasks
                }
                for future in futures:
                    img, src, path = futures[future]
                    try:
                        if future.result():
                            img['src'] = os.path.relpath(path, article_dir)
                            if img.has_attr('srcset'): del img['srcset']
                    except Exception as exc:
                        if "timeout" in str(exc).lower():
                            logger.warning(f"⚠️  Image download timed out: {src}")
                        else:
                            logger.warning(f"Image failed: {src}. Error: {exc}")

            # 6. Save Files
            html_content = str(final_soup)
            self._save_html(article_dir, article_meta.folder_name, html_content)
            
            if self.save_markdown:
                markdown_content = f"# Source: {url}\n\n"
                # Simple fallback: Convert the whole final HTML
                markdown_content += f"\n\n---\n\n{md(html_content)}"
                self._save_markdown(article_dir, article_meta.folder_name, markdown_content)
            
            # 7. Metadata JSON
            with open(os.path.join(article_dir, "meta.json"), "w", encoding="utf-8") as f:
                json.dump(article_meta.to_dict(), f, indent=2, ensure_ascii=False)
            
            # 8. Export
            if self.pdf_export:
                Exporter.to_pdf(page, os.path.join(article_dir, f"{article_meta.folder_name}.html"), 
                               os.path.join(article_dir, f"{article_meta.folder_name}.pdf"))
            if self.epub_export:
                Exporter.to_epub(article_meta.title, article_meta.author, html_content, assets_dir, 
                               os.path.join(article_dir, f"{article_meta.folder_name}.epub"))
            
            # Success
            article_meta.status = 'success'
            self.record_manager.save_record(article_meta.to_dict())
            logger.info(f"✅ Completed: {article_meta.folder_name}")
            return None

        except Exception as e:
            logger.critical(f"Critical error: {e}", exc_info=True)
            meta = ArticleMetadata(url=url, status='failed', failure_reason=f"Critical: {str(e)}")
            self.record_manager.save_record(meta.to_dict())
            result.error_msg = str(e)
            return result

    def _save_html(self, folder: str, title: str, content: str):
        path = os.path.join(folder, f"{title}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _save_markdown(self, folder: str, filename_base: str, content: str):
        path = os.path.join(folder, f"{filename_base}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

def main():
    parser = argparse.ArgumentParser(description="Universal Article Downloader (Plugin Architecture)")
    parser.add_argument("input", nargs="?", help="URL or file with URLs")
    parser.add_argument("--cookies", "-c", default="input/cookies.txt")
    parser.add_argument("--output", "-o", default="output")
    parser.add_argument("--headless", action="store_false", dest="headless", help="Show browser window")
    parser.add_argument("--scroll", type=int, default=Config.DEFAULT_SCROLL_COUNT)
    parser.add_argument("--timeout", type=int, default=Config.DEFAULT_TIMEOUT)
    parser.add_argument("--markdown", action="store_true", help="Save as Markdown")
    parser.add_argument("--pdf", action="store_true", help="Export as PDF")
    parser.add_argument("--epub", action="store_true", help="Export as EPUB")
    parser.add_argument("--force", action="store_true", help="Force redownload")
    
    parser.set_defaults(headless=Config.HEADLESS, markdown=False)
    args = parser.parse_args()

    # Interactive mode if no input provided
    if not args.input:
        print("Please enter the URL or file path:")
        try:
            args.input = input().strip()
        except EOFError:
            return

    if not args.input:
        print("No input provided. Exiting.")
        return

    # Prepare URLs
    urls = []
    if os.path.isfile(args.input):
        with open(args.input, 'r') as f:
            urls = [l.strip().strip('"\'“”') for l in f if l.strip() and not l.strip().startswith("#")]
    else:
        urls = [args.input.strip().strip('"\'“”')]

    if not urls: return

    downloader = XDownloader(args.output, args.markdown, args.pdf, args.epub)
    failures = []

    try:
        with sync_playwright() as p:
            logger.info(f"Launching Chromium (Headless: {args.headless})")
            browser = p.chromium.launch(headless=args.headless)
            context = browser.new_context(viewport={"width": 1280, "height": 1080}, user_agent=Config.USER_AGENT)

            cookies = load_cookies(args.cookies)
            if cookies:
                context.add_cookies([c for c in cookies if c.get('name') != 'lang'])
                logger.info(f"Cookies loaded.")

            page = context.new_page()

            for url in urls:
                result = downloader.process_url(page, url, args.scroll, args.timeout, args.force)
                if result:
                    failures.append(result.__dict__)

            browser.close()
    finally:
        downloader.close()
    
    logger.info("Generating Index...")
    IndexGenerator(args.output, ordered_urls=urls).generate()
    
    if failures:
        fail_path = os.path.join(args.output, "failures.json")
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(failures, f, indent=2, ensure_ascii=False)
    
    logger.info("Finished.")
if __name__ == "__main__":
    main()
