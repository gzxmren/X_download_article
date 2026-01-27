import os
import sys
import time
import argparse
import hashlib
import json
from playwright.sync_api import sync_playwright, Page
from markdownify import markdownify as md
from bs4 import BeautifulSoup

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

    def _download_image(self, page: Page, src: str, output_dir: str) -> str:
        """Downloads an image and returns the local filepath."""
        if not src: return None
        try:
            filename = hashlib.md5(src.encode()).hexdigest() + ".jpg"
            filepath = os.path.join(output_dir, filename)
            
            if os.path.exists(filepath):
                return filepath
                
            response = page.request.get(src)
            if response.status == 200:
                with open(filepath, "wb") as f:
                    f.write(response.body())
                return filepath
        except Exception as e:
            logger.warning(f"Image download failed: {src} ({e})")
        return None

    def process_url(self, page: Page, url: str, scroll_count: int, timeout: int, force: bool = False):
        if not force and self.history.exists(url):
            logger.info(f"⏭️  Skipping already downloaded: {url}")
            return

        logger.info(f"Processing URL: {url}")
        try:
            # 1. Navigate
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            
            logger.info(f"Waiting for content (timeout: {timeout}s)...")
            try:
                page.wait_for_selector("article", timeout=timeout * 1000)
                time.sleep(3) # Wait for hydration
            except:
                logger.error(f"Timeout loading {url}. Skipping.")
                return

            # 2. Scroll
            logger.info(f"Scrolling {scroll_count} times...")
            for _ in range(scroll_count):
                page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(1.2)

            # 3. Parse & Extract Metadata
            extractor = XArticleExtractor(page.content(), url)
            if not extractor.is_valid():
                logger.error("No article found in page content.")
                return

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
            
            final_markdown = f"# Source: {url}\n\n"
            
            articles = final_soup.find_all("article")
            
            for article in articles:
                # Download Images
                imgs = article.find_all("img")
                for img in imgs:
                    src = img.get("src")
                    if src and "profile_images" not in src:
                        local_path = self._download_image(page, src, assets_dir)
                        if local_path:
                            # Rewrite src to relative path
                            img['src'] = os.path.relpath(local_path, article_dir)
                            if img.has_attr('srcset'): del img['srcset']

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

        except Exception as e:
            logger.critical(f"Critical error processing {url}: {e}", exc_info=True)

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
            # Strip whitespace and various quote characters
            urls = [line.strip().strip('"\'“”') for line in f if line.strip() and not line.startswith("#")]
    else:
         urls = [args.input.strip().strip('"\'“”')]

    if not urls:
        logger.warning("No URLs to process.")
        return

    # Initialize Engine
    downloader = XDownloader(args.output, args.markdown)

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
            context.add_cookies(cookies)
            logger.info(f"Loaded {len(cookies)} cookies.")
        else:
            logger.warning("Running without cookies (Guest Mode). Content may be limited.")

        page = context.new_page()

        for url in urls:
            downloader.process_url(page, url, args.scroll, args.timeout, args.force)

        browser.close()
    
    # Generate Index after all tasks
    logger.info("Generating Global Index...")
    indexer = IndexGenerator(args.output)
    indexer.generate()
    logger.info("All tasks completed.")

if __name__ == "__main__":
    main()