import os
import yaml
from pathlib import Path
from .logger import logger

class ConfigLoader:
    """Singleton to load and hold configuration."""
    _instance = None
    _config = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Loads config.yaml, falling back to defaults if missing."""
        # Defaults
        self._config = {
            "app": {
                "timeout": 30,
                "scroll_count": 5,
                "headless": True,
                "max_workers": 8,
                "items_per_page": 20,
                "max_filename_length": 64,
                "max_topic_length": 40,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            "selectors": {
                "x_com": {
                    "article": "article",
                    "time": "time",
                    "user_name": "div[data-testid='User-Name']",
                    "tweet_text": "div[data-testid='tweetText']",
                    "article_title": "div[data-testid='twitter-article-title']",
                    "article_content": "div[data-testid='twitterArticleRichTextView']",
                    "images": "img"
                }
            }
        }

        # Try to load yaml from project root
        # We assume config.py is in src/, so project root is one level up
        project_root = Path(__file__).parent.parent
        yaml_path = project_root / "config.yaml"
        
        if yaml_path.exists():
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._merge(self._config, user_config)
                logger.info(f"Loaded configuration from {yaml_path}")
            except Exception as e:
                logger.error(f"Failed to load config.yaml: {e}. Using defaults.")
        else:
            logger.warning(f"config.yaml not found at {yaml_path}. Using internal defaults.")

    def _merge(self, base, update):
        """Deep merge dictionaries."""
        for k, v in update.items():
            if isinstance(v, dict) and k in base:
                self._merge(base[k], v)
            else:
                base[k] = v

    def get(self, path: str, default=None):
        """Access config using dot notation (e.g., 'app.timeout')."""
        keys = path.split('.')
        val = self._config
        try:
            for key in keys:
                val = val[key]
            return val
        except KeyError:
            return default

# Initialize Singleton
_loader = ConfigLoader()

# Static Accessor Class (Backwards Compatible API)
class Config:
    # App
    DEFAULT_TIMEOUT = _loader.get("app.timeout")
    DEFAULT_SCROLL_COUNT = _loader.get("app.scroll_count")
    HEADLESS = _loader.get("app.headless")
    MAX_WORKERS = _loader.get("app.max_workers")
    ITEMS_PER_PAGE = _loader.get("app.items_per_page")
    MAX_FILENAME_LENGTH = _loader.get("app.max_filename_length")
    MAX_TOPIC_LENGTH = _loader.get("app.max_topic_length")
    USER_AGENT = _loader.get("app.user_agent")
    PROXY = _loader.get("app.proxy")

    # Selectors
    class Selectors:
        _x = _loader.get("selectors.x_com")
        ARTICLE = _x.get("article")
        TIME = _x.get("time")
        USER_NAME = _x.get("user_name")
        TWEET_TEXT = _x.get("tweet_text")
        ARTICLE_TITLE = _x.get("article_title")
        ARTICLE_CONTENT = _x.get("article_content")
        IMAGES = _x.get("images")