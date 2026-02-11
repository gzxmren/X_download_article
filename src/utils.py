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
    Robust navigation with 'Fail Fast' strategy.
    
    1. Fast Probe (10s): Quickly checks if the server is responsive.
    2. Full Retry: If probe fails, retries with full configured timeout.
    """
    logger.info(f"Navigating to {url}...")
    
    # 1. Fast Probe (10s)
    try:
        # Use 'domcontentloaded' - 'networkidle' is too flaky on X.com due to constant polling
        page.goto(url, wait_until="domcontentloaded", timeout=10000)
        # Ensure the specific content is visible (this is the key check)
        # Using a shorter timeout here as well for the probe
        page.wait_for_selector(wait_selector, state="visible", timeout=10000)
        return
    except (PlaywrightTimeoutError, Exception) as e:
        logger.warning(f"⚠️  Fast probe failed (10s), retrying with full timeout ({timeout}s)...")

    # 2. Full Attempt (Configured Timeout)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        page.wait_for_selector(wait_selector, state="visible", timeout=timeout * 1000)
    except Exception as e:
        logger.warning(f"Navigation attempt failed for {url}: {e}")
        raise e
