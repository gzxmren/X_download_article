import pytest
from datetime import datetime
from src.models import ArticleMetadata, DownloadResult

def test_article_metadata_defaults():
    """Test that ArticleMetadata initializes with expected defaults."""
    meta = ArticleMetadata(url="https://x.com/test")
    assert meta.url == "https://x.com/test"
    assert meta.title == "Untitled"
    assert meta.status == "pending"
    assert isinstance(meta.download_time, str)
    # Check if download_time is a valid ISO format
    datetime.fromisoformat(meta.download_time)

def test_article_metadata_to_dict():
    """Test that to_dict produces the correct fields for RecordManager."""
    meta = ArticleMetadata(
        url="https://x.com/test",
        title="Sample Article",
        author="Tester",
        date="2024-03-08",
        folder_name="Tester_Sample_2024",
        local_path="path/to/file.html",
        status="success",
        failure_reason="",
        source="cli"
    )
    d = meta.to_dict()
    assert d['url'] == "https://x.com/test"
    assert d['status'] == "success"
    assert d['published_date'] == "2024-03-08"
    assert d['folder_name'] == "Tester_Sample_2024"
    assert d['local_path'] == "path/to/file.html"
    assert d['source'] == "cli"
    assert 'timestamp' in d

def test_download_result_initialization():
    """Test DownloadResult basic properties."""
    meta = ArticleMetadata(url="https://x.com/test")
    res = DownloadResult(url="https://x.com/test", success=True, metadata=meta)
    assert res.success is True
    assert res.metadata.url == "https://x.com/test"
    assert isinstance(res.timestamp, str)
