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
            'folder_name', 'local_path', 'timestamp', 'failure_reason', 'source'
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
        """Loads records into memory with automatic schema migration."""
        if not os.path.exists(self.csv_path):
            return

        try:
            needs_migration = False
            loaded_records = {}
            
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                f.seek(0, os.SEEK_END)
                if f.tell() == 0: return
                f.seek(0)

                reader = csv.DictReader(f)
                
                # Check if we need to migrate (missing local_path or other fields)
                if reader.fieldnames:
                    missing_fields = set(self.fieldnames) - set(reader.fieldnames)
                    if missing_fields:
                        logger.warning(f"Schema mismatch. Missing fields: {missing_fields}. Migrating...")
                        needs_migration = True

                for row in reader:
                    url = row.get('url')
                    if url:
                        # Defensive Filtering: Keep only known fields to prevent DictWriter errors
                        filtered_row = {field: row.get(field, "") for field in self.fieldnames}
                        loaded_records[url] = filtered_row
            
            self._records = loaded_records
            logger.info(f"Loaded {len(self._records)} records.")
            
            if needs_migration:
                self._commit()
                logger.info("Database schema migrated to latest version.")
                
        except Exception as e:
            logger.error(f"Failed to load records: {e}")
            self._handle_corruption()

    def _handle_corruption(self):
        """Backs up corrupted file and starts fresh."""
        if os.path.exists(self.csv_path):
            backup_name = f"{self.csv_path}.corrupted.{int(datetime.now().timestamp())}"
            shutil.copy(self.csv_path, backup_name)
            logger.warning(f"⚠️ Database backup created: {backup_name}")
            self._records = {}

    def is_downloaded(self, url: str) -> bool:
        record = self._records.get(url)
        return record is not None and record.get('status') == 'success'

    def save_record(self, data: dict):
        """Standard atomic save (updates memory and commits to disk)."""
        self.update_record_memory(data)
        self._commit()

    def update_record_memory(self, data: dict):
        """Updates memory cache only (for batch operations)."""
        url = data.get('url')
        if not url: return

        # Date and Time Logic (with legacy support)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        published_date = data.get('published_date') or data.get('date', 'NoDate')
        
        # Priority: timestamp -> download_time -> current_time
        timestamp = data.get('timestamp') or data.get('download_time') or current_time
        
        def sanitize(val):
            if val and isinstance(val, str) and val[0] in ('=', '+', '-', '@'):
                return "'" + val
            return val

        new_record = {
            'url': url,
            'status': data.get('status', 'unknown'),
            'title': sanitize(data.get('title', 'Untitled')),
            'author': sanitize(data.get('author', 'Unknown')),
            'published_date': published_date,
            'folder_name': data.get('folder_name', ''),
            'local_path': data.get('local_path', ''),
            'timestamp': timestamp,
            'failure_reason': data.get('failure_reason', ''),
            'source': data.get('source', 'cli')
        }

        # Preservation Logic
        existing = self._records.get(url)
        if existing and existing['status'] == 'success' and new_record['status'] == 'failed':
            return
        
        self._records[url] = new_record

    def _commit(self):
        """Atomic write to disk."""
        temp_path = self.csv_path + ".tmp"
        try:
            with open(temp_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(self._records.values())
            os.replace(temp_path, self.csv_path)
        except Exception as e:
            logger.error(f"Commit failed: {e}")

    def get_stats(self) -> dict:
        total = len(self._records)
        success = sum(1 for r in self._records.values() if r['status'] == 'success')
        failed = sum(1 for r in self._records.values() if r['status'] == 'failed')
        return {"total": total, "success": success, "failed": failed}

    def get_all_records(self) -> list:
        return list(self._records.values())
