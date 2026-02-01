import os
from bs4 import BeautifulSoup
import re
from typing import Optional, Tuple, List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from .utils import sanitize_filename, get_filename_from_url
from .logger import logger
from .config import Config

# Initialize Jinja2 Env relative to this file
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")
env = Environment(loader=FileSystemLoader(templates_dir))

class XArticleExtractor:
    """
    Responsible for parsing X (Twitter) HTML content and rendering clean local copies.
    """
    def __init__(self, html_content: str, url: str):
        self.soup = BeautifulSoup(html_content, "html.parser")
        self.url = url
        self.main_article = self.soup.find(Config.Selectors.ARTICLE)

    def is_valid(self) -> bool:
        return self.main_article is not None

    def get_articles(self) -> List[BeautifulSoup]:
        """Returns all article tags (main tweet + replies)."""
        return self.soup.find_all(Config.Selectors.ARTICLE)

    def _extract_styles(self, soup: BeautifulSoup) -> str:
        """
        Extracts all <style> tags from the source HTML to preserve high-fidelity layout.
        """
        style_tags = soup.find_all("style")
        return "\n".join([str(s) for s in style_tags])

    def get_clean_html(self) -> str:
        """
        Generates a clean, high-fidelity HTML string using Jinja2 templates.
        """
        # 1. Create a copy to avoid modifying original soup
        clean_soup = BeautifulSoup(str(self.soup), "html.parser")
        
        # 2. Strip unnecessary/dangerous tags
        for tag in clean_soup(["script", "noscript", "iframe"]):
            tag.decompose()

        # 3. Extract content fragments
        articles = clean_soup.find_all(Config.Selectors.ARTICLE)
        if not articles:
            return str(clean_soup) # Fallback if no article tags found

        # 4. Prepare data for template
        article_strings = [str(a) for a in articles]
        page_title = clean_soup.title.string if clean_soup.title else "X Article"
        
        # 5. Extract original styles for fidelity
        injected_styles = self._extract_styles(clean_soup)

        # 6. Render final HTML
        try:
            template = env.get_template("article.html")
            return template.render(
                title=page_title, 
                articles=article_strings, 
                styles=injected_styles
            )
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return str(clean_soup)

    def extract_metadata(self) -> str:
        """
        Extracts Date, Author, and Topic to form a folder name.
        Format: Author_Topic_Date
        """
        if not self.main_article:
            return get_filename_from_url(self.url)

        try:
            # 1. Date
            date_str = "NoDate"
            time_tag = self.main_article.find(Config.Selectors.TIME)
            if time_tag and time_tag.has_attr('datetime'):
                date_str = time_tag['datetime'].split('T')[0]

            # 2. Author
            author = "Unknown"
            user_div = self.main_article.select_one(Config.Selectors.USER_NAME)
            if user_div:
                text = user_div.get_text(separator=" ", strip=True)
                match = re.search(r'(@\w+)', text)
                if match:
                    author = match.group(1).strip('@')
                else:
                    author = text.split('·')[0].strip().replace(" ", "")

            # 3. Topic
            topic = "Image_Only"
            page_title = self.soup.title.string if self.soup.title else ""
            if page_title:
                match = re.search(r'[:：]\s*["“](.+?)["”]\s*/\s*X$', page_title)
                if match:
                    topic = match.group(1).strip()[:Config.MAX_TOPIC_LENGTH]
            
            if topic == "Image_Only":
                text_div = self.main_article.select_one(Config.Selectors.TWEET_TEXT)
                if text_div:
                    full_text = text_div.get_text(separator=" ", strip=True)
                    if full_text:
                        topic = full_text[:Config.MAX_TOPIC_LENGTH]

            raw_name = f"{author}_{topic}_{date_str}"
            return sanitize_filename(raw_name)

        except Exception as e:
            logger.warning(f"Metadata extraction warning: {e}")
            return get_filename_from_url(self.url)

    def get_meta_dict(self) -> dict:
        """Returns structured metadata for JSON export."""
        date_str = "Unknown"
        author = "Unknown"
        topic = "Untitled"
        
        if self.main_article:
            try:
                # Date
                time_tag = self.main_article.find(Config.Selectors.TIME)
                if time_tag and time_tag.has_attr('datetime'):
                    date_str = time_tag['datetime'].split('T')[0]
                
                # Author
                user_div = self.main_article.select_one(Config.Selectors.USER_NAME)
                if user_div:
                    text = user_div.get_text(separator=" ", strip=True)
                    match = re.search(r'(@\w+)', text)
                    author = match.group(1).strip('@') if match else text.split('·')[0].strip()

                # Topic
                page_title = self.soup.title.string if self.soup.title else ""
                if page_title:
                    match = re.search(r'[:：]\s*["“](.+?)["”]\s*/\s*X$', page_title)
                    if match:
                        topic = match.group(1).strip()
                
                if topic == "Untitled":
                     text_div = self.main_article.select_one(Config.Selectors.TWEET_TEXT)
                     if text_div:
                         topic = text_div.get_text(separator=" ", strip=True)[:100]
            except Exception as e:
                logger.warning(f"Error building meta dict: {e}")

        return {
            "url": self.url,
            "author": author,
            "date": date_str,
            "title": topic,
            "download_time": datetime.now().isoformat()
        }