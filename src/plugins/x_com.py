import os
import re
from urllib.parse import urlparse
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
        try:
            parsed = urlparse(url)
            # Security: Only allow http and https schemes
            if parsed.scheme not in ('http', 'https'):
                return False
            
            # Security: Strict domain whitelist
            domain = parsed.netloc.lower()
            if ":" in domain:
                domain = domain.split(":")[0]
                
            allowed_domains = {
                'x.com', 'www.x.com', 
                'twitter.com', 'www.twitter.com',
                'mobile.twitter.com'
            }
            return domain in allowed_domains
        except Exception:
            return False

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
        match = re.search(r'/status/(\d+)', url)
        if match:
            self.tweet_id = match.group(1)

        candidates = self._select_all(self.soup, "article")

        if self.tweet_id:
            for art in candidates:
                if art.find("a", href=re.compile(f"/status/{self.tweet_id}")):
                    self.main_article = art
                    break

        if not self.main_article and candidates:
            self.main_article = candidates[0]

    def _select_one(self, element, selector_key: str):
        """Try multiple selectors from config for a single element."""
        selectors = self.selectors.get(selector_key)
        if not selectors:
            return None
        if isinstance(selectors, str):
            selectors = [selectors]

        for sel in selectors:
            found = element.select_one(sel)
            if found:
                return found
        return None

    def _select_all(self, element, selector_key: str):
        """Try multiple selectors from config and return all matches for the first successful one."""
        selectors = self.selectors.get(selector_key)
        if not selectors:
            return []
        if isinstance(selectors, str):
            selectors = [selectors]

        for sel in selectors:
            found = element.select(sel)
            if found:
                return found
        return []

    def is_valid(self) -> bool:
        return self.main_article is not None

    def extract_metadata_obj(self) -> ArticleMetadata:
        meta = ArticleMetadata(url=self.url)
        if not self.main_article:
            meta.folder_name = get_filename_from_url(self.url)
            return meta

        try:
            # 1. Date
            time_tag = self._select_one(self.main_article, "time")
            if time_tag and time_tag.has_attr('datetime'):
                meta.date = time_tag['datetime'].split('T')[0]

            # 2. Author
            user_div = self._select_one(self.main_article, "user_name")
            if user_div:
                text = user_div.get_text(separator=" ", strip=True)
                match = re.search(r'(@\w+)', text)
                if match:
                    meta.author = match.group(1).strip('@')
                else:
                    meta.author = text.split('·')[0].strip().replace(" ", "")

            # 3. Topic / Title
            topic = ""

            # A. Try Longform Article Title first
            art_title_div = self._select_one(self.main_article, "article_title")
            if art_title_div:
                topic = art_title_div.get_text(strip=True)

            # B. Try Page Title
            if not topic:
                page_title = self.soup.title.string if self.soup.title else ""
                if page_title:
                    match = re.search(r'[:：]\s*["“](.+?)["”]\s*/\s*X$', page_title)
                    if match:
                        topic = match.group(1).strip()

            # C. Try Tweet Text fallback
            if not topic:
                text_div = self._select_one(self.main_article, "tweet_text")
                if text_div:
                    full_text = text_div.get_text(separator=" ", strip=True)
                    if full_text:
                        topic = full_text[:100]

            if not topic:
                topic = "Image_Only"

            meta.title = topic

            id_suffix = f"_{self.tweet_id}" if self.tweet_id else ""
            raw_folder = f"{meta.author}_{topic[:40]}{id_suffix}_{meta.date}"
            meta.folder_name = sanitize_filename(raw_folder)

        except Exception as e:
            logger.warning(f"Metadata extraction warning: {e}")
            meta.folder_name = get_filename_from_url(self.url)

        return meta

    def get_clean_html(self) -> str:
        clean_soup = BeautifulSoup(str(self.soup), "html.parser")

        for tag in clean_soup(["script", "noscript", "iframe", "object", "embed"]):
            tag.decompose()

        for meta in clean_soup.find_all("meta", attrs={"http-equiv": re.compile("refresh", re.I)}):
            meta.decompose()

        for tag in clean_soup.find_all(True):
            for attr in list(tag.attrs):
                if attr.lower().startswith("on"):
                    del tag[attr]

        main_art_in_clean = None
        if self.tweet_id:
            candidates = self._select_all(clean_soup, "article")
            for art in candidates:
                if art.find("a", href=re.compile(f"/status/{self.tweet_id}")):
                    main_art_in_clean = art
                    break

        if main_art_in_clean:
            articles = [main_art_in_clean]
        else:
            articles = self._select_all(clean_soup, "article")

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
        images = []
        articles = self._select_all(soup, "article")
        for article in articles:
            imgs = self._select_all(article, "images")
            for img in imgs:
                src = img.get("src")
                if src and "profile_images" not in src:
                    images.append((img, src))
        return images