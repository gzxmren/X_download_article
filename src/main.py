import os
import sys
import time
import argparse
import hashlib
import json
import requests
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
from src.history import HistoryManager
from src.indexer import IndexGenerator

class XDownloader:
    def __init__(self, output_root: str, save_markdown: bool = True):
        self.output_root = output_root
        self.save_markdown = save_markdown
        self.history = HistoryManager() # Log directory defaults to logs/

    @staticmethod
    def _download_task(session, url: str, save_path: str) -> bool:
        """
        Executes a single image download task using requests.
        Returns True if successful, False otherwise.
        """
        try:
            # Use stream=True to avoid loading large files into memory at once
            with session.get(url, stream=True, timeout=10) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return True
        except Exception as e:
            # logger.warning(f"Download failed for {url}: {e}") # Too noisy for threads
            return False

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
        page.wait_for_selector("article", timeout=timeout * 1000)
        time.sleep(3) # Wait for hydration

    def process_url(self, page: Page, url: str, scroll_count: int, timeout: int, force: bool = False) -> bool:
        """
        Returns True if successful (or skipped), False if failed.
        """
        if not force and self.history.exists(url):
            logger.info(f"⏭️  Skipping already downloaded: {url}")
            return True

        logger.info(f"Processing URL: {url}")
        try:
            # 1. Navigate with Retry
            try:
                self._safe_navigate(page, url, timeout)
            except Exception as e:
                logger.error(f"❌ Failed to load {url} after retries: {e}")
                return False

            # 2. Scroll
            logger.info(f"Scrolling {scroll_count} times...")
            for _ in range(scroll_count):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(1.2)

            # 3. Parse & Extract Metadata
            extractor = XArticleExtractor(page.content(), url)
            if not extractor.is_valid():
                logger.error("No article found in page content.")
                return False

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
            
            # Identify a User-Agent to match Playwright
            ua = page.evaluate("navigator.userAgent")
            session.headers.update({"User-Agent": ua})

            # Collect tasks
            download_tasks = []
            articles = final_soup.find_all("article")
            
            for article in articles:
                imgs = article.find_all("img")
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
                with ThreadPoolExecutor(max_workers=8) as executor:
                    # Submit all tasks
                    future_to_img = {
                        executor.submit(self._download_task, session, src, path): (img, src, path)
                        for img, src, path in download_tasks
                    }
                    
                    # Process results as they complete
                    for future in future_to_img:
                        img, src, path = future_to_img[future]
                        try:
                            if future.result():
                                # Success: Update src to local path
                                img['src'] = os.path.relpath(path, article_dir)
                                if img.has_attr('srcset'): del img['srcset']
                            else:
                                # Failure: Keep remote src, add marker
                                logger.warning(f"Failed to download image: {src}")
                                img['data-download-status'] = "failed"
                        except Exception as exc:
                            logger.error(f"Image task exception: {exc}")
                            img['data-download-status'] = "error"
            
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
            
            self.history.add(url)
            logger.info(f"✅ Download completed: {folder_name}")
            return True

        except Exception as e:
            logger.critical(f"Critical error processing {url}: {e}", exc_info=True)
            return False

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
    parser.add_argument("--headless", action="store_false", dest="headless", help="Show browser window")
    parser.add_argument("--scroll", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--markdown", action="store_true", help="Also save as Markdown format (Default: HTML only)")
    parser.add_argument("--force", action="store_true", help="Force redownload even if in history")
    
    parser.set_defaults(headless=True, markdown=False)
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
    downloader = XDownloader(args.output, args.markdown)
    failed_urls = []

    with sync_playwright() as p:
        logger.info(f"Launching browser (Headless: {args.headless})")
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(
            viewport={"width": 1280, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
            success = downloader.process_url(page, url, args.scroll, args.timeout, args.force)
            if not success:
                failed_urls.append(url)

        browser.close()
    
    # Generate Index after all tasks
    logger.info("Generating Global Index...")
    indexer = IndexGenerator(args.output, ordered_urls=urls)
    indexer.generate()
    
    # Report Failures
    if failed_urls:
        fail_path = os.path.join(args.output, "failures.txt")
        logger.warning(f"⚠️  {len(failed_urls)} URLs failed. Saving list to {fail_path}")
        with open(fail_path, "w", encoding="utf-8") as f:
            for url in failed_urls:
                f.write(f"{url}\n")
    
    logger.info("All tasks completed.")

if __name__ == "__main__":
    main()