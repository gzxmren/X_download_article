import os
import json
from datetime import datetime

class IndexGenerator:
    def __init__(self, output_root: str, ordered_urls: list = None):
        self.output_root = output_root
        self.index_file = os.path.join(output_root, "index.html")
        self.ordered_urls = ordered_urls or []

    def generate(self):
        """Scans all subdirectories for meta.json and rebuilds index.html"""
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
        
        # Generate HTML
        self._write_html(articles)
        print(f"📊 Index updated with {len(articles)} articles.")

    def _write_html(self, articles):
        rows = ""
        for art in articles:
            # Find first image as thumbnail if available (not implemented in meta yet, using placeholder)
            # Future improvement: save thumbnail path in meta.json
            title = art.get('title', 'Untitled')
            author = art.get('author', 'Unknown')
            date = art.get('date', 'Unknown')
            url = art.get('url', '#')
            link = art.get('local_path', '#')
            
            rows += f"""
            <tr class="hover:bg-gray-50 transition">
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{date}</td>
                <td class="px-6 py-4">
                    <div class="text-sm font-medium text-gray-900"><a href="{link}" class="hover:text-blue-600">{title}</a></div>
                    <div class="text-sm text-gray-500"><a href="{url}" target="_blank" class="text-xs text-blue-400 hover:underline">Original Source</a></div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{author}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <a href="{link}" class="text-indigo-600 hover:text-indigo-900">View Local</a>
                </td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>X Articles Library</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen p-8">
    <div class="max-w-6xl mx-auto bg-white shadow-lg rounded-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200 bg-white flex justify-between items-center">
            <h1 class="text-2xl font-bold text-gray-800">📚 X Articles Library</h1>
            <span class="text-sm text-gray-500">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
        
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Topic</th>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Author</th>
                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Action</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {rows}
                </tbody>
            </table>
        </div>
        
        <div class="px-6 py-4 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
            Total Articles: {len(articles)}
        </div>
    </div>
</body>
</html>"""
        
        with open(self.index_file, "w", encoding="utf-8") as f:
            f.write(html)
