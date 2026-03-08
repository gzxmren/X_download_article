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
from src.utils import load_cookies, safe_navigate, validate_and_fix_url
from src.logger import logger
from src.indexer import IndexGenerator
from src.config import Config
from src.exporter import Exporter
from src.record_manager import RecordManager
from src.models import ArticleMetadata, DownloadResult
from src.plugin_manager import PluginManager
from src.exceptions import (
    XDownloaderError, NavigationTimeoutError, PlatformBlockedError,
    ExtractionError, PluginNotFoundError
)

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
        self.session.trust_env = True
        
        if Config.PROXY:
            self.session.proxies = {
                "http": Config.PROXY,
                "https": Config.PROXY,
            }
            logger.info(f"Using proxy for downloads: {Config.PROXY}")

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

    def _get_plugin(self, url: str):
        try:
            return self.plugin_manager.get_plugin(url)
        except ValueError as e:
            raise PluginNotFoundError(str(e))

    def _navigate_and_scroll(self, page: Page, url: str, scroll_count: int, timeout: int, plugin):
        try:
            safe_navigate(page, url, timeout, plugin.get_wait_selector())
        except Exception as e:
            is_timeout = isinstance(e, PlaywrightTimeoutError) or "timeout" in str(e).lower()
            if is_timeout:
                raise NavigationTimeoutError(f"Network Timeout: {str(e)}")
            
            # Simple check for block/deleted
            page_content = page.content().lower()
            if "suspended" in page_content or "blocked" in page_content or "captcha" in page_content:
                raise PlatformBlockedError(f"Platform Blocked: {str(e)}")
            
            raise XDownloaderError(f"Navigation: {str(e)}")

        if scroll_count > 0:
            logger.info(f"Scrolling {scroll_count} times...")
            for _ in range(scroll_count):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(1.2)

    def _extract_content(self, page: Page, url: str, plugin):
        extractor = plugin.get_extractor(page.content(), url)
        if not extractor.is_valid():
            raise ExtractionError("No article content found")
        return extractor

    def _handle_images(self, page: Page, extractor, article_dir: str):
        assets_dir = os.path.join(article_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        # Sync cookies
        pw_cookies = page.context.cookies()
        for cookie in pw_cookies:
            self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

        raw_html = extractor.get_clean_html()
        soup = BeautifulSoup(raw_html, "html.parser")
        images = extractor.get_content_images(soup)
        
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
                    logger.warning(f"Image failed: {src}. Error: {exc}")
        
        return soup

    def _save_assets(self, article_dir: str, article_meta, final_soup: BeautifulSoup, url: str):
        html_content = str(final_soup)
        self._save_html(article_dir, article_meta.folder_name, html_content)
        
        if self.save_markdown:
            markdown_content = f"# Source: {url}\n\n"
            markdown_content += f"\n\n---\n\n{md(html_content)}"
            self._save_markdown(article_dir, article_meta.folder_name, markdown_content)
        
        with open(os.path.join(article_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(article_meta.to_dict(), f, indent=2, ensure_ascii=False)
        
        return html_content

    def _export_formats(self, page: Page, article_dir: str, article_meta, html_content: str):
        assets_dir = os.path.join(article_dir, "assets")
        if self.pdf_export:
            Exporter.to_pdf(page, os.path.join(article_dir, f"{article_meta.folder_name}.html"), 
                           os.path.join(article_dir, f"{article_meta.folder_name}.pdf"))
        if self.epub_export:
            Exporter.to_epub(article_meta.title, article_meta.author, html_content, assets_dir, 
                           os.path.join(article_dir, f"{article_meta.folder_name}.epub"))

    def process_url(self, page: Page, url: str, scroll_count: int, timeout: int, force: bool = False) -> Optional[DownloadResult]:
        """Processes a single URL with fine-grained error handling."""
        if not force and self.record_manager.is_downloaded(url):
            logger.info(f"⏭️  Skipping already downloaded: {url}")
            return None

        logger.info(f"Processing URL: {url}")
        result = DownloadResult(url=url, success=False)
        
        try:
            plugin = self._get_plugin(url)
            self._navigate_and_scroll(page, url, scroll_count, timeout, plugin)
            extractor = self._extract_content(page, url, plugin)
            
            article_meta = extractor.extract_metadata_obj()
            article_dir = os.path.join(self.output_root, article_meta.folder_name)
            
            final_soup = self._handle_images(page, extractor, article_dir)
            html_content = self._save_assets(article_dir, article_meta, final_soup, url)
            self._export_formats(page, article_dir, article_meta, html_content)

            # Finalize Success
            article_meta.status = 'success'
            self.record_manager.save_record(article_meta.to_dict())
            logger.info(f"✅ Completed: {article_meta.folder_name}")
            return None

        except (NavigationTimeoutError, PlatformBlockedError) as e:
            logger.error(f"❌ {type(e).__name__}: {url} - {e}")
            meta = ArticleMetadata(url=url, status='failed', failure_reason=str(e))
            self.record_manager.save_record(meta.to_dict())
            result.error_msg = str(e)
            return result
        except ExtractionError as e:
            logger.error(f"❌ Extraction Error: {url} - {e}")
            meta = ArticleMetadata(url=url, status='failed', failure_reason="No article content found")
            self.record_manager.save_record(meta.to_dict())
            result.error_msg = str(e)
            return result
        except PluginNotFoundError as e:
            logger.error(f"❌ Plugin Error: {url} - {e}")
            result.error_msg = str(e)
            return result
        except Exception as e:
            logger.critical(f"Critical error on {url}: {e}", exc_info=True)
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

def _process_urls_in_session(downloader: XDownloader, args, urls_to_process: List[str]):
    failures = []
    
    browser = None
    context = None
    try:
        with sync_playwright() as p:
            logger.info(f"Launching Chromium (Headless: {args.headless})")
            
            launch_kwargs = {"headless": args.headless}
            if Config.PROXY:
                launch_kwargs["proxy"] = {"server": Config.PROXY}
                
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(viewport={"width": 1280, "height": 1080}, user_agent=Config.USER_AGENT)

            cookies = load_cookies(args.cookies)
            if cookies:
                context.add_cookies([c for c in cookies if c.get('name') != 'lang'])
                logger.info(f"Cookies loaded.")

            page = context.new_page()

            for url in urls_to_process:
                try:
                    result = downloader.process_url(page, url, args.scroll, args.timeout, args.force)
                    if result:
                        failures.append(result.__dict__)
                except KeyboardInterrupt:
                    logger.warning(f"\n⚠️  Interrupted by user. Cleaning up...")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error processing {url}: {e}")
                    continue

            if browser:
                browser.close()
    except Exception as e:
        logger.critical(f"Critical browser error: {e}")
    finally:
        # Emergency cleanup if context manager fails
        try:
            if downloader: downloader.close()
        except: pass
    
    logger.info("Generating Index...")
    # Pass only successfully processed URLs to IndexGenerator if needed, or all initially planned.
    # For now, keeping the original behavior of passing all initially planned URLs.
    IndexGenerator(args.output, ordered_urls=urls_to_process).generate()
    
    if failures:
        fail_path = os.path.join(args.output, "failures.json")
        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(failures, f, indent=2, ensure_ascii=False)
    
    logger.info("Finished.")
    return failures

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

    raw_urls = []
    
    # Check for input from arguments first
    if args.input:
        logger.info(f"Reading input from argument: {args.input}")
        if os.path.isfile(args.input):
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    raw_urls = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
            except Exception as e:
                logger.error(f"Failed to read input file: {e}")
                return
        else:
            raw_urls = [args.input.strip()]
            
    # If no argument input, check for piped input
    elif not sys.stdin.isatty():
        logger.info("Reading input from stdin (pipe)...")
        raw_urls = [line.strip() for line in sys.stdin if line.strip()]

    # If we have URLs from args or pipe, process them
    if raw_urls:
        urls = []
        for r_url in raw_urls:
            valid_url = validate_and_fix_url(r_url)
            if valid_url:
                urls.append(valid_url)
            else:
                logger.warning(f"⚠️  Skipping invalid URL: {r_url}")
        
        if not urls:
            logger.error("No valid URLs to process.")
            return
            
        logger.info(f"Processing {len(urls)} valid URLs...")
        downloader = XDownloader(args.output, args.markdown, args.pdf, args.epub)
        _process_urls_in_session(downloader, args, urls)
        return # Exit after processing

    # Otherwise, enter true interactive mode
    logger.info("Entering interactive mode. Enter URL or file path, or type 'quit' to exit.")
    while True:
        try:
            user_input = input(">>> ").strip()
        except EOFError:
            logger.info("EOF detected. Exiting interactive mode.")
            break

        if not user_input:
            continue
        
        if user_input.lower() in ['quit', 'exit']:
            logger.info("Exiting interactive mode.")
            break

        interactive_raw_urls = []
        if os.path.isfile(user_input):
            try:
                with open(user_input, 'r', encoding='utf-8') as f:
                    interactive_raw_urls = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
            except Exception as e:
                logger.error(f"Failed to read input file: {e}")
                continue
        else:
            interactive_raw_urls = [user_input]

        interactive_urls = []
        for r_url in interactive_raw_urls:
            valid_url = validate_and_fix_url(r_url)
            if valid_url:
                interactive_urls.append(valid_url)
            else:
                logger.warning(f"⚠️  Skipping invalid URL: {r_url}")
        
        if not interactive_urls:
            logger.error("No valid URLs to process from your input.")
            continue
        
        logger.info(f"Processing {len(interactive_urls)} valid URLs from input...")
        
        # Create a new downloader for each interactive turn to ensure clean sessions
        current_downloader = XDownloader(args.output, args.markdown, args.pdf, args.epub)
        _process_urls_in_session(current_downloader, args, interactive_urls)
if __name__ == "__main__":
    main()
