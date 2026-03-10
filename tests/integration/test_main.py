import os
import pytest
from unittest.mock import MagicMock, patch, mock_open
from src.main import XDownloader
from src.models import ArticleMetadata

@pytest.fixture
def downloader(tmp_path):
    """Fixture to create XDownloader instance with temp output root."""
    output_root = tmp_path / "output"
    output_root.mkdir()
    return XDownloader(str(output_root))

def test_process_url_already_downloaded(downloader):
    """Test that it skips URL if already downloaded according to record_manager."""
    url = "https://x.com/already_saved"
    # Mock record_manager.is_downloaded to return True
    with patch.object(downloader.record_manager, 'is_downloaded', return_value=True):
        res = downloader.process_url(MagicMock(), url, scroll_count=0, timeout=30)
        assert res is None

@patch('src.main.safe_navigate')
def test_process_url_success(mock_navigate, downloader):
    """Test successful URL processing by mocking key components."""
    url = "https://x.com/test_success"
    page_mock = MagicMock()
    
    # Mock Plugin & Extractor
    mock_plugin = MagicMock()
    mock_extractor = MagicMock()
    mock_meta = ArticleMetadata(url=url, title="Test", author="Author", folder_name="Author_Test")
    
    mock_plugin.get_extractor.return_value = mock_extractor
    mock_extractor.is_valid.return_value = True
    mock_extractor.extract_metadata_obj.return_value = mock_meta
    mock_extractor.get_clean_html.return_value = "<div>Content</div>"
    mock_extractor.get_content_images.return_value = []
    
    # Setup mocks in downloader
    with patch.object(downloader, '_get_plugin', return_value=mock_plugin), \
         patch.object(downloader, '_save_assets', return_value="html"), \
         patch.object(downloader, '_export_formats'), \
         patch.object(downloader.record_manager, 'is_downloaded', return_value=False), \
         patch.object(downloader.record_manager, 'save_record'):
        
        res = downloader.process_url(page_mock, url, scroll_count=0, timeout=30)
        assert res is None
        # Verify success side-effects
        assert mock_meta.status == 'success'
        assert downloader.record_manager.save_record.called

@patch('src.main.safe_navigate')
def test_process_url_extraction_error(mock_navigate, downloader):
    """Test handling of ExtractionError."""
    url = "https://x.com/test_fail"
    page_mock = MagicMock()
    
    # Mock Plugin & Extractor
    mock_plugin = MagicMock()
    mock_extractor = MagicMock()
    
    mock_plugin.get_extractor.return_value = mock_extractor
    mock_extractor.is_valid.return_value = False # Cause error
    
    with patch.object(downloader, '_get_plugin', return_value=mock_plugin), \
         patch.object(downloader.record_manager, 'is_downloaded', return_value=False), \
         patch.object(downloader.record_manager, 'save_record'):
        
        res = downloader.process_url(page_mock, url, scroll_count=0, timeout=30)
        assert res is not None
        assert res.success is False
        assert "No article content found" in res.error_msg
        assert downloader.record_manager.save_record.called
