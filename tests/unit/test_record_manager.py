import os
import csv
import pytest
from src.record_manager import RecordManager

@pytest.fixture
def temp_csv(tmp_path):
    """Creates a temporary CSV file path for testing."""
    return str(tmp_path / "test_records.csv")

def test_init_creates_csv(temp_csv):
    """Test that initialization creates the CSV file with headers."""
    rm = RecordManager(temp_csv)
    assert os.path.exists(temp_csv)
    with open(temp_csv, 'r') as f:
        header = f.readline().strip()
        assert header == "url,status,title,author,published_date,folder_name,timestamp,failure_reason,source"

def test_save_and_read_memory(temp_csv):
    """Test saving a record updates memory and file."""
    rm = RecordManager(temp_csv)
    data = {
        'url': 'http://test.com/1',
        'status': 'success',
        'title': 'Test Title',
        'author': 'Tester',
        'date': '2024-01-01',
        'folder_name': 'Tester_Test_2024'
    }
    rm.save_record(data)
    
    # Check Memory (O(1) lookup)
    assert rm.is_downloaded('http://test.com/1')
    assert not rm.is_downloaded('http://test.com/2')
    
    # Check File Persistence
    with open(temp_csv, 'r') as f:
        content = f.read()
        assert 'http://test.com/1' in content
        assert 'Tester_Test_2024' in content

def test_do_not_overwrite_success_with_failure(temp_csv):
    """Test that a 'success' record is not overwritten by a 'failed' one."""
    rm = RecordManager(temp_csv)
    url = 'http://test.com/stable'
    
    # 1. Save Success
    rm.save_record({'url': url, 'status': 'success', 'title': 'Good'})
    assert rm.is_downloaded(url)
    
    # 2. Try to Save Failure (should be ignored)
    rm.save_record({'url': url, 'status': 'failed', 'failure_reason': 'Network Error'})
    
    # Check that status is still success
    record = rm._records[url]
    assert record['status'] == 'success'
    
def test_atomic_write_recovery(temp_csv):
    """
    Simulate a corruption by writing garbage to a file, 
    then ensure RecordManager handles it gracefully (via backup or reset).
    NOTE: Our current impl backs up and resets on load error.
    """
    # Create corrupted file
    with open(temp_csv, 'w') as f:
        f.write("GARBAGE_DATA_NO_CSV_STRUCTURE")
        
    rm = RecordManager(temp_csv)
    # Should start empty but safe
    assert len(rm._records) == 0
    
    # Should have created a backup (check directory)
    dir_path = os.path.dirname(temp_csv)
    files = os.listdir(dir_path)
    backups = [f for f in files if "corrupted" in f]
    assert len(backups) > 0
