import os
from src.clean_urls import deduplicate_urls

def test_deduplicate_urls_removes_dupes(tmp_path):
    """Test that duplicates are removed while order and comments are preserved."""
    # 1. Setup mock file
    file_path = tmp_path / "urls.txt"
    content = """
    # Section 1
    https://x.com/user1/status/123
    https://x.com/user2/status/456
    
    # Section 2
    https://x.com/user1/status/123
    "https://x.com/user3/status/789"
    """
    file_path.write_text(content, encoding='utf-8')

    # 2. Run functionality
    deduplicate_urls(str(file_path))

    # 3. Verify
    result = file_path.read_text(encoding='utf-8').splitlines()
    # Filter out empty lines for easier counting, but keep logic checks
    non_empty = [l.strip() for l in result if l.strip()]
    
    assert '# Section 1' in non_empty
    assert 'https://x.com/user1/status/123' in non_empty
    assert 'https://x.com/user2/status/456' in non_empty
    assert '"https://x.com/user3/status/789"' in non_empty # Should preserve quotes if that's the logic
    
    # Count occurrences of user1 (should be 1)
    user1_count = sum(1 for l in non_empty if 'user1/status/123' in l)
    assert user1_count == 1

def test_deduplicate_nonexistent_file(capsys):
    """Test error handling for missing file."""
    deduplicate_urls("non_existent_file.txt")
    captured = capsys.readouterr()
    assert "Error: File 'non_existent_file.txt' not found" in captured.out
