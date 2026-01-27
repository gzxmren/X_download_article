import os
import re
import hashlib
import json
from urllib.parse import urlparse

def sanitize_filename(text: str) -> str:
    """
    Sanitizes a string to be safe for file systems.
    """
    # Remove invalid characters
    text = re.sub(r'[\\/*?:\"<>|]', "", text)
    text = text.replace("\n", " ").replace("\r", "")
    text = re.sub(r'\s+', "_", text).strip("_")
    return text[:100]

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
