from abc import ABC, abstractmethod
from typing import List, Tuple, Any
from bs4 import Tag
from .models import ArticleMetadata

class IExtractor(ABC):
    """
    Standard interface for parsing HTML from any platform.
    """
    @abstractmethod
    def is_valid(self) -> bool:
        """Return True if content was successfully parsed."""
        pass

    @abstractmethod
    def extract_metadata_obj(self) -> ArticleMetadata:
        """Return structured metadata."""
        pass

    @abstractmethod
    def get_clean_html(self) -> str:
        """Return the final HTML string to be saved."""
        pass

    @abstractmethod
    def get_content_images(self, soup: Any) -> List[Tuple[Tag, str]]:
        """
        Return a list of (img_tag, src_url) for images within the provided soup object.
        The downloader will update the img_tag's 'src' attribute in-place.
        """
        pass

class IPlugin(ABC):
    """
    Top-level plugin interface.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the plugin (e.g., 'x_com')."""
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this plugin can process the given URL."""
        pass

    @abstractmethod
    def get_wait_selector(self) -> str:
        """Return the CSS selector to wait for after navigation."""
        pass

    @abstractmethod
    def get_extractor(self, html_content: str, url: str) -> IExtractor:
        """Return an instance of the extractor for this page."""
        pass
