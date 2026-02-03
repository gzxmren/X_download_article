import sys
import os
import pytest

# Add project root to sys.path so we can import src modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

@pytest.fixture
def mock_html_content():
    """Returns HTML content loaded from a static fixture file."""
    fixture_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "integration", "fixtures", "tweet_sample.html"
    )
    with open(fixture_path, "r", encoding="utf-8") as f:
        return f.read()
