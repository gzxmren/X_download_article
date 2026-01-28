import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    # --- Behavior ---
    DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", 20))
    DEFAULT_SCROLL_COUNT = int(os.getenv("DEFAULT_SCROLL_COUNT", 5))
    HEADLESS = os.getenv("HEADLESS", "True").lower() == "true"
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 8))
    ITEMS_PER_PAGE = int(os.getenv("ITEMS_PER_PAGE", 20))
    
    # --- Telegram Notification (Disabled) ---
    # TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "False").lower() == "true"
    # TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    # TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # --- Batch Processing (Disabled) ---
    # BATCH_INTERVAL_MINUTES = int(os.getenv("BATCH_INTERVAL_MINUTES", 60))
    # URLS_FILE = os.getenv("URLS_FILE", "input/urls.txt")

    # --- Browser ---
    USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # --- Selectors ---
    class Selectors:
        ARTICLE = os.getenv("SELECTOR_ARTICLE", "article")
        TIME = os.getenv("SELECTOR_TIME", "time")
        USER_NAME = os.getenv("SELECTOR_USER_NAME", "div[data-testid='User-Name']")
        TWEET_TEXT = os.getenv("SELECTOR_TWEET_TEXT", "div[data-testid='tweetText']")
        IMAGES = "img" # Usually standard, but kept here for consistency if needed
