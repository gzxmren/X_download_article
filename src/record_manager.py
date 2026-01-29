import csv
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from .logger import logger

class RecordManager:
    def __init__(self, csv_path: str = "output/records.csv"):
        self.csv_path = csv_path
        self.fieldnames = [
            'url', 'status', 'title', 'author', 'published_date', 
            'folder_name', 'timestamp', 'failure_reason', 'source'
        ]
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        if not os.path.exists(self.csv_path):
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def load_records(self) -> Dict[str, dict]:
        """Loads all records into a dictionary keyed by URL."""
        records = {}
        if not os.path.exists(self.csv_path):
            return records

        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records[row['url']] = row
        except Exception as e:
            logger.error(f"Failed to load records CSV: {e}")
            # Backup corrupted file
            if os.path.exists(self.csv_path):
                backup_name = f"{self.csv_path}.bak.{int(datetime.now().timestamp())}"
                shutil.copy(self.csv_path, backup_name)
                logger.warning(f"Backed up corrupted CSV to {backup_name}")
        
        return records

    def save_record(self, data: dict):
        """
        Upsert a record.
        Logic: 
        - If URL exists and is 'success', valid new 'failed' will be ignored (unless force update logic is added).
        - Otherwise, update/overwrite.
        """
        records = self.load_records()
        url = data.get('url')
        if not url:
            return

        # Defaults
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record_to_save = {
            'url': url,
            'status': data.get('status', 'unknown'),
            'title': data.get('title', ''),
            'author': data.get('author', ''),
            'published_date': data.get('date', ''), # Map 'date' to 'published_date'
            'folder_name': data.get('folder_name', ''), # Map 'local_path' or folder
            'timestamp': current_time,
            'failure_reason': data.get('failure_reason', ''),
            'source': data.get('source', 'cli')
        }

        # Check existing
        existing = records.get(url)
        if existing:
            # Policy: Don't overwrite SUCCESS with FAILED
            if existing['status'] == 'success' and record_to_save['status'] == 'failed':
                logger.info(f"💾 Record check: Keeping existing SUCCESS for {url} despite recent failure.")
                return
            
            # Policy: Preserve older info if new info is missing
            if not record_to_save['title'] and existing['title']:
                record_to_save['title'] = existing['title']
            if not record_to_save['author'] and existing['author']:
                record_to_save['author'] = existing['author']
            
        # Update dict
        records[url] = record_to_save
        
        # Write back (Memory dump approach for consistency)
        self._write_all(records.values())

    def _write_all(self, rows):
        """Rewrites the entire CSV."""
        temp_path = self.csv_path + ".tmp"
        try:
            with open(temp_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            os.replace(temp_path, self.csv_path)
        except Exception as e:
            logger.error(f"Failed to write records CSV: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def get_stats(self):
        records = self.load_records()
        total = len(records)
        success = sum(1 for r in records.values() if r['status'] == 'success')
        failed = sum(1 for r in records.values() if r['status'] == 'failed')
        return {"total": total, "success": success, "failed": failed}

    def is_downloaded(self, url: str) -> bool:
        """Checks if a URL has been successfully downloaded."""
        records = self.load_records()
        record = records.get(url)
        return record is not None and record.get('status') == 'success'
