import pytest
from unittest.mock import MagicMock, call
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from src.utils import safe_navigate

def test_safe_navigate_success():
    """Test that safe_navigate calls goto and wait_for_selector with full timeout."""
    mock_page = MagicMock()
    url = "http://example.com"
    timeout = 30
    selector = "div.content"

    safe_navigate(mock_page, url, timeout, selector)

    # Should call goto with full timeout (30 * 1000 = 30000ms)
    mock_page.goto.assert_called_once_with(url, wait_until="domcontentloaded", timeout=30000)
    
    # Should check selector visibility with full timeout
    # Note: safe_navigate now uses a combined selector
    combined_selector = f"{selector}, div[data-testid='tweetText'], div[data-testid='twitterArticleRichTextView']"
    mock_page.wait_for_selector.assert_called_once_with(combined_selector, state="visible", timeout=30000)

def test_safe_navigate_fail_goto():
    """Test that safe_navigate raises exception if goto fails."""
    mock_page = MagicMock()
    url = "http://example.com"
    timeout = 30
    selector = "div.content"

    mock_page.goto.side_effect = Exception("Goto Failed")

    with pytest.raises(Exception, match="Goto Failed"):
        safe_navigate(mock_page, url, timeout, selector)

    assert mock_page.goto.call_count == 1
    assert mock_page.wait_for_selector.call_count == 0

def test_safe_navigate_fail_wait_selector():
    """Test that safe_navigate raises exception if wait_for_selector fails."""
    mock_page = MagicMock()
    url = "http://example.com"
    timeout = 30
    selector = "div.content"

    mock_page.goto.return_value = None
    mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("Selector Timeout")

    with pytest.raises(PlaywrightTimeoutError, match="Selector Timeout"):
        safe_navigate(mock_page, url, timeout, selector)

    assert mock_page.goto.call_count == 1
    assert mock_page.wait_for_selector.call_count == 1
