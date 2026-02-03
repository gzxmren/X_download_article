import os
import sys
import re
from bs4 import BeautifulSoup

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.plugins.x_com import XExtractor

def debug_extraction(html_path, url):
    if not os.path.exists(html_path):
        print(f"File not found: {html_path}")
        return

    print(f"📂 Loading: {html_path}")
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    extractor = XExtractor(html_content, url)
    print(f"🎯 Target Tweet ID: {extractor.tweet_id}")

    if not extractor.main_article:
        print("❌ No main_article found by XExtractor.")
        return

    print("-" * 40)
    print("✅ XExtractor Selected Article:")
    text = extractor.main_article.get_text(separator=" ", strip=True)[:200]
    print(f"   Text: {text}...")
    
    # Check why it was selected
    print("\n🔍 Analysis:")
    if extractor.tweet_id:
        # Re-run the search logic to see what happened
        candidates = extractor.soup.select("article")
        print(f"   Total articles in DOM: {len(candidates)}")
        
        found_by_id = False
        for i, art in enumerate(candidates):
            # Relaxed regex for debugging
            link = art.find("a", href=re.compile(extractor.tweet_id))
            if link:
                print(f"   👉 Article #{i} contains ID link: {link['href']}")
                print(f"      Text: {art.get_text(separator=' ', strip=True)[:50]}...")
                found_by_id = True
            
        if not found_by_id:
            print("   ❌ No article contains a link with the Tweet ID.")
            print("   ⚠️  Fallback logic was used (First Article).")

if __name__ == "__main__":
    # Default to the known debug file if available
    debug_dir = os.path.join(project_root, "output", "debug")
    files = sorted([f for f in os.listdir(debug_dir) if f.endswith(".html")], reverse=True)
    
    if files:
        latest_html = os.path.join(debug_dir, files[0])
        # Use the problematic URL
        target_url = "https://x.com/EXM7777/status/2017659658425758193?s=20"
        debug_extraction(latest_html, target_url)
    else:
        print("No debug HTML files found. Run diagnose_url.py first.")
