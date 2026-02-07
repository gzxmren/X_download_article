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
        self._records: Dict[str, dict] = {}
        self._ensure_csv_exists()
        self._load_all_to_memory()

    def _ensure_csv_exists(self):
        """Initializes the CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.csv_path):
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            try:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                    writer.writeheader()
                logger.info(f"Initialized new records database at {self.csv_path}")
            except Exception as e:
                logger.error(f"Failed to initialize CSV: {e}")

    def _load_all_to_memory(self):
        """Loads all records into memory once to enable O(1) lookups."""
        if not os.path.exists(self.csv_path):
            return

        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                # Check for empty file
                f.seek(0, os.SEEK_END)
                if f.tell() == 0:
                    return
                f.seek(0)

                reader = csv.DictReader(f)
                
                # Strict Header Check
                if reader.fieldnames != self.fieldnames:
                     raise ValueError("CSV Headers do not match expected schema.")

                # Filter out empty rows or rows with no URL
                self._records = {row['url']: row for row in reader if row.get('url')}
            
            logger.info(f"Loaded {len(self._records)} records into memory cache.")
        except Exception as e:
            logger.error(f"Failed to load records into memory: {e}")
            self._handle_corruption()

    def _handle_corruption(self):
        """Backs up corrupted file and starts fresh."""
        if os.path.exists(self.csv_path):
            backup_name = f"{self.csv_path}.corrupted.{int(datetime.now().timestamp())}"
            shutil.copy(self.csv_path, backup_name)
            logger.warning(f"⚠️  Database corrupted. Backed up to {backup_name}. Starting with empty cache.")
            self._records = {}

    def is_downloaded(self, url: str) -> bool:
        """Fast O(1) check using memory cache."""
        record = self._records.get(url)
        return record is not None and record.get('status') == 'success'

    def save_record(self, data: dict):
        """
        Updates memory cache and performs an atomic write to disk.
        """
        url = data.get('url')
        if not url:
            logger.warning("Attempted to save record without URL.")
            return

        # Prepare normalized record
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Support both 'date' and 'published_date' keys for compatibility
        published_date = data.get('published_date') or data.get('date', 'NoDate')
        
        # CSV Injection Protection: Prepend ' to values starting with risky characters
        def sanitize_csv_field(val: str) -> str:
            if val and isinstance(val, str) and val[0] in ('=', '+', '-', '@'):
                return "'" + val
            return val

        new_record = {
            'url': url,
            'status': data.get('status', 'unknown'),
            'title': sanitize_csv_field(data.get('title', 'Untitled')),
            'author': sanitize_csv_field(data.get('author', 'Unknown')),
            'published_date': published_date,
            'folder_name': data.get('folder_name', ''),
            'timestamp': current_time,
            'failure_reason': data.get('failure_reason', ''),
            'source': data.get('source', 'cli')
        }

        # Policy: Prevent overwriting 'success' with 'failed'
        existing = self._records.get(url)
        if existing:
            if existing['status'] == 'success' and new_record['status'] == 'failed':
                logger.debug(f"Skipping update for {url}: Preservation of successful status.")
                return
            
            # Preserve existing metadata if new metadata is missing
            if new_record['title'] == 'Untitled' and existing.get('title'):
                new_record['title'] = existing['title']
            if new_record['author'] == 'Unknown' and existing.get('author'):
                new_record['author'] = existing['author']
            if not new_record['folder_name'] and existing.get('folder_name'):
                new_record['folder_name'] = existing['folder_name']

        # Update Memory
        self._records[url] = new_record
        
        # Commit to Disk (Atomic)
        self._commit()

    def _commit(self):
        """
        Performs an atomic write to the CSV file.
        Uses a temporary file and os.replace to ensure data integrity.
        """
        temp_path = self.csv_path + ".tmp"
        try:
            with open(temp_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(self._records.values())
            os.replace(temp_path, self.csv_path)
        except Exception as e:
            logger.error(f"CRITICAL: Atomic write failed for {self.csv_path}: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def get_stats(self) -> dict:
        """Returns stats from memory cache."""
        total = len(self._records)
        success = sum(1 for r in self._records.values() if r['status'] == 'success')
        failed = sum(1 for r in self._records.values() if r['status'] == 'failed')
        return {"total": total, "success": success, "failed": failed}
