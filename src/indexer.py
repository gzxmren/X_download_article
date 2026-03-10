import os
import json
from urllib.parse import quote
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from .config import Config

# Initialize Jinja2 Env
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_dir, "templates")
env = Environment(loader=FileSystemLoader(templates_dir))

class IndexGenerator:
    def __init__(self, output_root: str, ordered_urls: list = None):
        self.output_root = output_root
        self.ordered_urls = ordered_urls or []

    def generate(self, records: list = None):
        """
        Builds index.html. 
        Uses provided records (from RecordManager memory cache) for fast generation,
        or falls back to scanning the disk if no records are provided.
        """
        articles = []
        
        if records:
            # --- Fast Path: Use provided memory-cached records ---
            for rec in records:
                if rec.get('status') != 'success':
                    continue
                
                folder_name = rec.get('folder_name')
                if not folder_name:
                    continue
                
                # Lightweight Liveness Check: Only check if folder exists, don't read meta.json
                full_folder_path = os.path.join(self.output_root, folder_name)
                if os.path.isdir(full_folder_path):
                    articles.append(self._format_record_for_index(rec))
        else:
            # --- Legacy/Fallback Path: Scan disk (slow, 800+ IOs) ---
            articles = self._scan_disk_for_articles()

        # Sort Logic (Initial backend sort)
        # Sort by timestamp (new) or download_time (legacy) descending
        articles.sort(key=lambda x: x.get('timestamp') or x.get('download_time', '0000-00-00'), reverse=True)
        
        total_articles = len(articles)
        
        # Generate single index.html with embedded data
        file_path = os.path.join(self.output_root, "index.html")
        
        try:
            template = env.get_template("index.html")
            # Serialize articles to JSON string for JS embedding
            articles_json = json.dumps(articles, ensure_ascii=False)
            
            html_content = template.render(
                articles_json=articles_json, # Pass JSON string
                total_count=total_articles,
                items_per_page=Config.ITEMS_PER_PAGE,
                generated_at=datetime.now().strftime('%Y-%m-%d %H:%M')
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"📊 Index updated: {total_articles} articles. (Client-side rendering enabled)")
            
        except Exception as e:
            print(f"Index generation failed: {e}")

    def _format_record_for_index(self, rec: dict) -> dict:
        """Normalizes a CSV record for the Jinja2 template using stored paths."""
        local_path = rec.get('local_path', '')
        
        # Build article object
        meta = rec.copy()
        
        if local_path:
            # path is stored as "folder/file.html", we need to quote each part
            parts = local_path.split('/')
            meta['local_path'] = "/".join([quote(p) for p in parts])
        else:
            # Fallback for old records without local_path
            folder_name = rec.get('folder_name', '')
            meta['local_path'] = f"{quote(folder_name)}/{quote(folder_name)}.html"
        
        # Date Display Logic
        raw_date = rec.get('timestamp') or rec.get('download_time')
        if raw_date and 'T' in raw_date:
            meta['date'] = raw_date.split('T')[0]
        elif raw_date and ' ' in raw_date:
            meta['date'] = raw_date.split(' ')[0]
        else:
            meta['date'] = rec.get('published_date') or "Unknown"
            
        return meta

    def _scan_disk_for_articles(self) -> list:
        """Legacy slow method: Scans disk for meta.json files."""
        articles = []
        if os.path.exists(self.output_root):
            for entry in os.scandir(self.output_root):
                if entry.is_dir():
                    meta_path = os.path.join(entry.path, "meta.json")
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                                folder_encoded = quote(entry.name)
                                fname = meta.get('folder_name') or meta.get('filename_base', 'article')
                                filename_encoded = quote(fname)
                                meta['local_path'] = f"{folder_encoded}/{filename_encoded}.html"
                                raw_date = meta.get('timestamp') or meta.get('download_time')
                                if raw_date:
                                    # Normalize both 'T' and ' ' separators
                                    if 'T' in raw_date:
                                        meta['date'] = raw_date.split('T')[0]
                                    elif ' ' in raw_date:
                                        meta['date'] = raw_date.split(' ')[0]
                                    else:
                                        meta['date'] = raw_date
                                else:
                                    meta['date'] = meta.get('published_date') or "Unknown"
                                articles.append(meta)
                        except Exception as e:
                            print(f"Error reading {meta_path}: {e}")
        return articles
