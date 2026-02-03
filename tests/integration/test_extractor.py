import pytest
from src.plugins.x_com import XExtractor
from src.models import ArticleMetadata

def test_extractor_validity(mock_html_content):
    """Test that extractor recognizes valid content."""
    # XExtractor init signature is (html_content, url)
    extractor = XExtractor(mock_html_content, "http://x.com/test")
    assert extractor.is_valid()

def test_metadata_extraction(mock_html_content):
    """Test extracting structured metadata from HTML."""
    extractor = XExtractor(mock_html_content, "http://x.com/test")
    meta = extractor.extract_metadata_obj()
    
    assert isinstance(meta, ArticleMetadata)
    assert meta.author == "TestUser"
    assert meta.date == "2024-01-01"
    assert "test tweet" in meta.title.lower() or "test article" in meta.title.lower()

def test_folder_naming(mock_html_content):
    """Test that folder names are sanitized and formatted correctly."""
    extractor = XExtractor(mock_html_content, "http://x.com/test")
    meta = extractor.extract_metadata_obj()
    folder_name = meta.folder_name
    
    # Format: Author_Topic_Date
    assert folder_name.startswith("TestUser_")
    assert "2024-01-01" in folder_name
    assert " " not in folder_name
