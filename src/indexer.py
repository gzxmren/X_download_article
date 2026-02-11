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

    def generate(self):
        """Scans all subdirectories for meta.json and rebuilds index.html with client-side search/sort."""
        articles = []
        
        # Scan directories
        if os.path.exists(self.output_root):
            for entry in os.scandir(self.output_root):
                if entry.is_dir():
                    meta_path = os.path.join(entry.path, "meta.json")
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                                # Ensure relative path is correct for linking
                                folder_encoded = quote(entry.name)
                                # Filename logic: folder_name (new) -> filename_base (legacy) -> default 'article'
                                fname = meta.get('folder_name') or meta.get('filename_base', 'article')
                                filename_encoded = quote(fname)
                                meta['local_path'] = f"{folder_encoded}/{filename_encoded}.html"
                                
                                # Date Display Logic: Use processing time (timestamp) as requested
                                # Fallback to published_date if timestamp is missing
                                raw_date = meta.get('timestamp') or meta.get('download_time')
                                
                                if raw_date:
                                    # Extract YYYY-MM-DD from ISO format
                                    meta['date'] = raw_date.split('T')[0]
                                else:
                                    # Legacy fallback
                                    meta['date'] = meta.get('published_date') or meta.get('date') or "Unknown"
                                    
                                articles.append(meta)
                        except Exception as e:
                            print(f"Error reading {meta_path}: {e}")

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
                generated_at=datetime.now().strftime('%Y-%m-%d %H:%M')
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"📊 Index updated: {total_articles} articles. (Client-side rendering enabled)")
            
        except Exception as e:
            print(f"Index generation failed: {e}")
