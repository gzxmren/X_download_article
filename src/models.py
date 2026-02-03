from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

@dataclass
class ArticleMetadata:
    """
    Structured metadata for an X article.
    Ensures type safety and provides a single source of truth for article data.
    """
    url: str
    title: str = "Untitled"
    author: str = "Unknown"
    date: str = "NoDate"
    folder_name: str = ""
    download_time: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending" # pending, success, failed
    failure_reason: str = ""
    source: str = "cli"

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV/JSON export, matching RecordManager fieldnames."""
        return {
            'url': self.url,
            'status': self.status,
            'title': self.title,
            'author': self.author,
            'published_date': self.date,
            'folder_name': self.folder_name,
            'timestamp': self.download_time,
            'failure_reason': self.failure_reason,
            'source': self.source
        }

@dataclass
class DownloadResult:
    """Represents the outcome of a single URL processing task."""
    url: str
    success: bool
    metadata: Optional[ArticleMetadata] = None
    error_msg: str = ""
    retry_attempts: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
