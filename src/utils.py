import os
import re
import hashlib
import json
from urllib.parse import urlparse
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from src.config import Config
from src.logger import logger

def sanitize_filename(text: str) -> str:
    """
    Sanitizes a string to be safe for file systems.
    """
    # 1. Remove control characters (0x00-0x1f)
    text = "".join(ch for ch in text if ord(ch) >= 32)
    
    # 2. Remove invalid characters for Windows/Linux
    text = re.sub(r'[\\/*?:\"<>|]', "", text)
    
    # 3. Handle whitespace and formatting
    text = text.replace("\n", " ").replace("\r", "")
    text = re.sub(r'\s+', "_", text).strip("_")
    
    # 4. Security: Prevent leading dots (path traversal / hidden files)
    while text.startswith("."):
        text = text[1:]
        
    # 5. Fallback for empty strings
    if not text:
        text = "untitled_article"
        
    return text[:Config.MAX_FILENAME_LENGTH]

def get_filename_from_url(url: str) -> str:
    """Fallback filename generation from URL."""
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_")
    if not path:
        path = "x_home"
    return path

def parse_netscape_cookies(file_path: str) -> list:
    """Parses a Netscape HTTP Cookie file into a list of dicts for Playwright."""
    cookies = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.startswith('#') and not line.startswith("#HttpOnly_"):
                continue
            if not line.strip():
                continue
            
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                domain = parts[0]
                http_only = False
                if domain.startswith("#HttpOnly_"):
                    domain = domain[10:]
                    http_only = True
                
                try:
                    cookie = {
                        "domain": domain,
                        "path": parts[2],
                        "secure": parts[3].upper() == 'TRUE',
                        "expires": int(parts[4]),
                        "name": parts[5],
                        "value": parts[6],
                        "httpOnly": http_only,
                        "sameSite": "Lax"
                    }
                    cookies.append(cookie)
                except ValueError:
                    continue
    return cookies

def load_cookies(file_path: str) -> list:
    """Smart loader for JSON or Netscape cookies."""
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return parse_netscape_cookies(file_path)

def safe_navigate(page: Page, url: str, timeout: int, wait_selector: str):
    """
    Robust navigation.
    
    Removed the 'Fast Probe' strategy as it causes issues with heavy sites like X.com
    where script bundles take a long time to load and shouldn't be interrupted.
    """
    logger.info(f"Navigating to {url}...")
    
    try:
        # Use 'domcontentloaded' - 'networkidle' is too flaky on X.com
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        
        # Ensure the specific content is visible (this is the key check)
        # We use a combined selector to be more robust
        combined_selector = f"{wait_selector}, div[data-testid='tweetText'], div[data-testid='twitterArticleRichTextView']"
        page.wait_for_selector(combined_selector, state="visible", timeout=timeout * 1000)
    except Exception as e:
        logger.warning(f"Navigation attempt failed for {url}: {e}")
        raise e

def validate_and_fix_url(url: str) -> str | None:
    """
    Validates and attempts to fix common URL typos.
    Returns the fixed URL string if valid, otherwise returns None.
    """
    if not url:
        return None
        
    fixed_url = url.strip().strip('"\'“”')
    
    # 1. Common Typo Fixes
    if fixed_url.startswith("hhttps://"):
        fixed_url = "https://" + fixed_url[8:]
    elif fixed_url.startswith("htpp://"):
        fixed_url = "http://" + fixed_url[7:]
    elif fixed_url.startswith("ttps://"):
        fixed_url = "https://" + fixed_url[7:]
    elif not fixed_url.startswith("http"):
        # Assume https for missing scheme
        fixed_url = "https://" + fixed_url

    # 2. Strict Validation Pattern
    # Matches http/https/ftp with a domain/ip and optional path
    pattern = re.compile(
        r'^(?:http|ftp)s?://' # scheme
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain
        r'localhost|' # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ip
        r'(?::\d+)?' # port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if pattern.match(fixed_url):
        return fixed_url
    
    return None
