import os
import json
import pytest
from src.indexer import IndexGenerator
from src.config import Config
from src.models import ArticleMetadata

def test_indexer_generates_pages(tmp_path):
    """Test that indexer scans directories and generates paginated HTML."""
    
    # 1. Setup Mock Output Directory
    output_root = tmp_path / "output"
    output_root.mkdir()
    
    # Create 25 mock articles
    items_needed = Config.ITEMS_PER_PAGE + 5
    
    for i in range(items_needed):
        folder_name = f"Article_{i}"
        article_dir = output_root / folder_name
        article_dir.mkdir()
        
        # Use SOURCE OF TRUTH (ArticleMetadata) to generate test data
        meta = ArticleMetadata(
            url=f"http://test.com/{i}",
            title=f"Test Article {i}",
            author="Tester",
            date="2024-01-01",
            folder_name=folder_name,
            download_time=f"2024-01-01T12:00:{i:02d}"
        )
        
        (article_dir / "meta.json").write_text(json.dumps(meta.to_dict()), encoding='utf-8')

    # 2. Run Indexer
    indexer = IndexGenerator(str(output_root))
    indexer.generate()
    
    # 3. Verify Files Exist
    index_1 = output_root / "index.html"
    index_2 = output_root / "index_2.html"
    
    assert index_1.exists()
    assert not index_2.exists() # Should no longer exist (Client-side pagination)
    
    # 4. Verify Content
    content_1 = index_1.read_text(encoding='utf-8')
    
    # Check for embedded JSON
    assert "const rawData = [" in content_1
    
    # Check if data is present in the JSON string
    assert f"Test Article {items_needed - 1}" in content_1
    assert "Test Article 0" in content_1
    
    # Verify Date Rendering (Crucial Check)
    assert "2024-01-01" in content_1
