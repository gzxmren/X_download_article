
import pytest
from unittest.mock import MagicMock
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from src.utils import safe_navigate

def test_safe_navigate_success_first_try():
    """Test that safe_navigate returns immediately if the first fast probe succeeds."""
    mock_page = MagicMock()
    url = "http://example.com"
    timeout = 30
    selector = "div.content"

    safe_navigate(mock_page, url, timeout, selector)

    # Should call goto with 10s timeout
    mock_page.goto.assert_called_once_with(url, wait_until="domcontentloaded", timeout=10000)
    # Should check selector visibility with 10s timeout
    mock_page.wait_for_selector.assert_called_once_with(selector, state="visible", timeout=10000)

def test_safe_navigate_retry_on_timeout():
    """Test that safe_navigate retries with full timeout if the first probe fails."""
    mock_page = MagicMock()
    url = "http://example.com"
    timeout = 30
    selector = "div.content"

    # First call (Probe) raises TimeoutError, Second call (Retry) succeeds
    mock_page.goto.side_effect = [PlaywrightTimeoutError("Timeout!"), None]
    
    safe_navigate(mock_page, url, timeout, selector)

    # Verify calls
    assert mock_page.goto.call_count == 2
    # First call (Probe)
    mock_page.goto.assert_any_call(url, wait_until="domcontentloaded", timeout=10000)
    # Second call (Retry with full timeout)
    mock_page.goto.assert_any_call(url, wait_until="domcontentloaded", timeout=30000)
    
    # Wait for selector should be called once (for the successful second attempt)
    # The probe's wait_for_selector is skipped because goto failed.
    mock_page.wait_for_selector.assert_called_once_with(selector, state="visible", timeout=30000)

def test_safe_navigate_fail_both_times():
    """Test that safe_navigate raises exception if both attempts fail."""
    mock_page = MagicMock()
    url = "http://example.com"
    timeout = 30
    selector = "div.content"

    # Both calls raise Exception
    mock_page.goto.side_effect = [Exception("First Fail"), Exception("Second Fail")]

    with pytest.raises(Exception, match="Second Fail"):
        safe_navigate(mock_page, url, timeout, selector)

    assert mock_page.goto.call_count == 2
