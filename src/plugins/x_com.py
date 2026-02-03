import os
import re
from typing import List, Tuple, Any
from bs4 import BeautifulSoup, Tag
from jinja2 import Environment, FileSystemLoader

from ..interfaces import IPlugin, IExtractor
from ..models import ArticleMetadata
from ..utils import sanitize_filename, get_filename_from_url
from ..config import ConfigLoader
from ..logger import logger

class XComPlugin(IPlugin):
    @property
    def name(self) -> str:
        return "x_com"

    def can_handle(self, url: str) -> bool:
        return "x.com" in url or "twitter.com" in url

    def get_wait_selector(self) -> str:
        selectors = ConfigLoader().get("selectors.x_com", {})
        # Prefer specific tweet content, fallback to generic article
        return selectors.get("article", "article")

    def get_extractor(self, html_content: str, url: str) -> IExtractor:
        return XExtractor(html_content, url)

class XExtractor(IExtractor):
    def __init__(self, html_content: str, url: str):
        self.soup = BeautifulSoup(html_content, "html.parser")
        self.url = url
        self.selectors = ConfigLoader().get("selectors.x_com", {})
        
        # Initialize Jinja2
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_src = os.path.dirname(current_dir)
        templates_dir = os.path.join(project_src, "templates")
        self.env = Environment(loader=FileSystemLoader(templates_dir))
        
        # --- Precise Anchoring Logic ---
        self.main_article = None
        self.tweet_id = None
        
        # 1. Extract Tweet ID from URL
        # URL format: .../status/123456789...
        match = re.search(r'/status/(\d+)', url)
        if match:
            self.tweet_id = match.group(1)
            
        article_sel = self.selectors.get("article", "article")
        candidates = self.soup.select(article_sel)
        
        if self.tweet_id:
            # 2. Find article containing link to this ID (Permalink)
            # The timestamp in a tweet is usually a link to the tweet itself
            for art in candidates:
                if art.find("a", href=re.compile(f"/status/{self.tweet_id}")):
                    self.main_article = art
                    break
        
        # Fallback: Use the first one if ID search fails (or no ID found)
        if not self.main_article and candidates:
            # Try to skip potential "sidebar" articles if they are distinct?
            # For now, first candidate is the best guess if ID match fails.
            self.main_article = candidates[0]

    def is_valid(self) -> bool:
        return self.main_article is not None

    def extract_metadata_obj(self) -> ArticleMetadata:
        meta = ArticleMetadata(url=self.url)
        if not self.main_article:
            meta.folder_name = get_filename_from_url(self.url)
            return meta

        try:
            # 1. Date
            time_sel = self.selectors.get("time", "time")
            time_tag = self.main_article.select_one(time_sel)
            if time_tag and time_tag.has_attr('datetime'):
                meta.date = time_tag['datetime'].split('T')[0]

            # 2. Author
            user_sel = self.selectors.get("user_name", "div[data-testid='User-Name']")
            user_div = self.main_article.select_one(user_sel)
            if user_div:
                text = user_div.get_text(separator=" ", strip=True)
                match = re.search(r'(@\w+)', text)
                if match:
                    meta.author = match.group(1).strip('@')
                else:
                    meta.author = text.split('·')[0].strip().replace(" ", "")

            # 3. Topic
            # Try to get from page title first as it's often cleanest
            page_title = self.soup.title.string if self.soup.title else ""
            topic = "Image_Only"
            
            if page_title:
                # Format: "User on X: 'Tweet Text' / X"
                match = re.search(r'[:：]\s*["“](.+?)["”]\s*/\s*X$', page_title)
                if match:
                    topic = match.group(1).strip()
            
            if topic == "Image_Only":
                text_sel = self.selectors.get("tweet_text", "div[data-testid='tweetText']")
                text_div = self.main_article.select_one(text_sel)
                if text_div:
                    full_text = text_div.get_text(separator=" ", strip=True)
                    if full_text:
                        topic = full_text[:100]
            
            meta.title = topic
            
            # Stable Naming: Include Tweet ID
            id_suffix = f"_{self.tweet_id}" if self.tweet_id else ""
            raw_folder = f"{meta.author}_{topic[:40]}{id_suffix}_{meta.date}"
            meta.folder_name = sanitize_filename(raw_folder)

        except Exception as e:
            logger.warning(f"Metadata extraction warning: {e}")
            meta.folder_name = get_filename_from_url(self.url)
            
        return meta

    def get_clean_html(self) -> str:
        clean_soup = BeautifulSoup(str(self.soup), "html.parser")
        
        # 1. Remove dangerous tags
        for tag in clean_soup(["script", "noscript", "iframe", "object", "embed"]):
            tag.decompose()
            
        # 2. Remove meta refresh (prevents auto-redirect)
        for meta in clean_soup.find_all("meta", attrs={"http-equiv": re.compile("refresh", re.I)}):
            meta.decompose()

        # 3. Strip event handlers (onload, onclick, etc.)
        for tag in clean_soup.find_all(True):
            for attr in list(tag.attrs):
                if attr.lower().startswith("on"):
                    del tag[attr]

        article_sel = self.selectors.get("article", "article")
        articles = clean_soup.select(article_sel)
        if not articles:
            return str(clean_soup)

        article_strings = [str(a) for a in articles]
        page_title = clean_soup.title.string if clean_soup.title else "X Article"
        
        style_tags = clean_soup.find_all("style")
        injected_styles = "\n".join([str(s) for s in style_tags])

        try:
            template = self.env.get_template("article.html")
            return template.render(
                title=page_title, 
                articles=article_strings, 
                styles=injected_styles
            )
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return str(clean_soup)

    def get_content_images(self, soup: Any) -> List[Tuple[Tag, str]]:
        """
        Finds images in the provided soup (which is the final HTML to be saved).
        """
        images = []
        article_sel = self.selectors.get("article", "article")
        img_sel = self.selectors.get("images", "img")
        
        articles = soup.select(article_sel)
        for article in articles:
            imgs = article.select(img_sel)
            for img in imgs:
                src = img.get("src")
                # Filter out profile images or standard X emojis if needed
                if src and "profile_images" not in src:
                    images.append((img, src))
        return images