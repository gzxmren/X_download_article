from bs4 import BeautifulSoup
import re
from typing import Optional, Tuple, List
from datetime import datetime
from .utils import sanitize_filename, get_filename_from_url
from .logger import logger

class XSelector:
    """Centralized configuration for CSS selectors."""
    ARTICLE = "article"
    TIME = "time"
    USER_NAME_DIV = "div[data-testid='User-Name']"
    TWEET_TEXT = "div[data-testid='tweetText']"
    IMAGES = "img"

class XArticleExtractor:
    """
    Responsible for parsing X (Twitter) HTML content.
    """
    def __init__(self, html_content: str, url: str):
        self.soup = BeautifulSoup(html_content, "html.parser")
        self.url = url
        self.main_article = self.soup.find(XSelector.ARTICLE)

    def is_valid(self) -> bool:
        return self.main_article is not None

    def get_articles(self) -> List[BeautifulSoup]:
        """Returns all article tags (main tweet + replies)."""
        return self.soup.find_all(XSelector.ARTICLE)

    def get_clean_html(self) -> str:
        """
        Returns a high-fidelity HTML string by keeping original styles
        but stripping UI noise (sidebar, nav, etc).
        """
        # Create a copy to avoid modifying the original soup used for other extractions
        clean_soup = BeautifulSoup(str(self.soup), "html.parser")
        
        # Remove scripts to prevent tracking/errors
        for script in clean_soup(["script", "noscript", "iframe"]):
            script.decompose()

        # Find the main container (react-root)
        body = clean_soup.find("body")
        if body:
            # We want to clear the body but keep the articles
            # Strategy: Extract articles, clear body, append articles back wrapped in a container
            articles = clean_soup.find_all(XSelector.ARTICLE)
            if not articles:
                return str(clean_soup) # Fallback

            # Clear body content
            body.clear()
            
            # Create a centered wrapper imitating Twitter's layout width
            wrapper = clean_soup.new_tag("div")
            wrapper['style'] = "max-width: 600px; margin: 0 auto; padding-top: 20px; font-family: TwitterChirp, -apple-system, BlinkMacSystemFont, sans-serif;"
            body.append(wrapper)

            # Re-attach articles
            for article in articles:
                # Wrap each article in a card-like div for better visibility
                card = clean_soup.new_tag("div")
                card['style'] = "border: 1px solid rgb(239, 243, 244); border-radius: 16px; margin-bottom: 16px; padding: 16px;"
                card.append(article)
                wrapper.append(card)

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
            time_tag = self.main_article.find(XSelector.TIME)
            if time_tag and time_tag.has_attr('datetime'):
                date_str = time_tag['datetime'].split('T')[0]

            # 2. Author
            author = "Unknown"
            user_div = self.main_article.select_one(XSelector.USER_NAME_DIV)
            if user_div:
                text = user_div.get_text(separator=" ", strip=True)
                match = re.search(r'(@\w+)', text)
                if match:
                    author = match.group(1).strip('@')
                else:
                    author = text.split('·')[0].strip().replace(" ", "")

            # 3. Topic
            topic = "Image_Only"
            
            # Strategy A: Try to extract from page <title> tag
            page_title = self.soup.title.string if self.soup.title else ""
            if page_title:
                match = re.search(r'[:：]\s*["“](.+?)["”]\s*/\s*X$', page_title)
                if match:
                    topic = match.group(1).strip()[:100]
            
            # Strategy B: Fallback to DOM
            if topic == "Image_Only":
                text_div = self.main_article.select_one(XSelector.TWEET_TEXT)
                if text_div:
                    full_text = text_div.get_text(separator=" ", strip=True)
                    if full_text:
                        topic = full_text[:100]

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
                time_tag = self.main_article.find(XSelector.TIME)
                if time_tag and time_tag.has_attr('datetime'):
                    date_str = time_tag['datetime'].split('T')[0]
                
                # Author
                user_div = self.main_article.select_one(XSelector.USER_NAME_DIV)
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
                     text_div = self.main_article.select_one(XSelector.TWEET_TEXT)
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