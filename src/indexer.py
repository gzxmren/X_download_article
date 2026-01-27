import os
import json
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
        """Scans all subdirectories for meta.json and rebuilds index.html with pagination."""
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
                                meta['local_path'] = f"{entry.name}/{meta.get('filename_base', 'article')}.html"
                                articles.append(meta)
                        except Exception as e:
                            print(f"Error reading {meta_path}: {e}")

        # Sort Logic
        if self.ordered_urls:
            # Create a map of url -> index for O(1) lookup
            url_order = {url: i for i, url in enumerate(self.ordered_urls)}
            
            # Helper to get index, default to infinity if not found (put at end)
            def get_order(article):
                return url_order.get(article.get('url', '').strip(), float('inf'))
            
            articles.sort(key=get_order)
        else:
            # Fallback to date sort if no order provided
            articles.sort(key=lambda x: x.get('date', '0000-00-00'), reverse=True)
        
        # Pagination Logic
        total_articles = len(articles)
        per_page = Config.ITEMS_PER_PAGE
        
        # Calculate chunks
        if total_articles > 0:
            chunks = [articles[i:i + per_page] for i in range(0, total_articles, per_page)]
        else:
            chunks = [[]] # Handle empty case
            
        total_pages = len(chunks)
        
        for i, chunk in enumerate(chunks):
            page_num = i + 1
            self._write_single_page(chunk, page_num, total_pages, total_articles)
            
        print(f"📊 Index updated: {total_articles} articles across {total_pages} pages.")

    def _write_single_page(self, articles_chunk, page_num, total_pages, total_count):
        # Determine filename
        if page_num == 1:
            filename = "index.html"
        else:
            filename = f"index_{page_num}.html"
            
        file_path = os.path.join(self.output_root, filename)
        
        # Determine Links
        prev_page = None
        if page_num > 1:
            prev_page = "index.html" if page_num == 2 else f"index_{page_num - 1}.html"
            
        next_page = None
        if page_num < total_pages:
            next_page = f"index_{page_num + 1}.html"

        try:
            template = env.get_template("index.html")
            html_content = template.render(
                articles=articles_chunk,
                total_count=total_count,
                generated_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
                current_page=page_num,
                total_pages=total_pages,
                prev_page=prev_page,
                next_page=next_page
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            print(f"Index generation failed for page {page_num}: {e}")
