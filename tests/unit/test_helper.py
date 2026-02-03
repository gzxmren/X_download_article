import os
import json
import argparse
from src.helper import cmd_sync
from src.record_manager import RecordManager

def test_cmd_sync_rebuilds_csv(tmp_path):
    """Test that 'sync' command scans directories and populates CSV."""
    
    # 1. Setup Mock Output Directory
    output_root = tmp_path / "output"
    output_root.mkdir()
    
    # Create an article folder with meta.json
    article_dir = output_root / "User_Topic_Date"
    article_dir.mkdir()
    meta = {
        "url": "http://test.com/sync",
        "title": "Synced Title",
        "author": "SyncedUser",
        "date": "2024-01-01"
    }
    (article_dir / "meta.json").write_text(json.dumps(meta), encoding='utf-8')
    
    # Setup CSV path (initially empty)
    csv_path = tmp_path / "records.csv"
    
    # 2. Run Sync Command
    # Mock args object
    args = argparse.Namespace(output=str(output_root), csv=str(csv_path))
    cmd_sync(args)
    
    # 3. Verify CSV Content
    rm = RecordManager(str(csv_path))
    assert rm.is_downloaded("http://test.com/sync")
    
    # Verify Metadata (need to peek into internal records or load them)
    # Since _records is populated on init:
    record = rm._records["http://test.com/sync"]
    assert record['title'] == "Synced Title"
    assert record['author'] == "SyncedUser"
    assert record['status'] == "success"
    assert record['source'] == "sync_scan"
