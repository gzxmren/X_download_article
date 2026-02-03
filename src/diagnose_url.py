import os
import sys
import time
import argparse
from playwright.sync_api import sync_playwright

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import Config
from src.utils import load_cookies
from src.logger import logger

def diagnose(url: str, times: int, cookies_path: str):
    output_dir = os.path.join(project_root, "output", "debug")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🕵️  Diagnosing URL: {url}")
    print(f"🔄 Repeating {times} times...")
    print(f"📂 Output directory: {output_dir}")

    with sync_playwright() as p:
        print("🚀 Launching Browser...")
        # Force headless=False if you want to watch, otherwise use Config
        # For diagnostics, screenshots are usually enough, so we stick to Config defaults or override if needed.
        # But seeing it live is often better for debugging. Let's respect Config for now but warn user.
        browser = p.chromium.launch(headless=Config.HEADLESS)
        context = browser.new_context(
            viewport={"width": 1280, "height": 1080},
            user_agent=Config.USER_AGENT
        )

        cookies = load_cookies(cookies_path)
        if cookies:
            context.add_cookies([c for c in cookies if c.get('name') != 'lang'])
            print(f"🍪 Loaded {len(cookies)} cookies.")
        else:
            print("⚠️  No cookies loaded!")

        for i in range(1, times + 1):
            print(f"\n--- Run {i}/{times} ---")
            page = context.new_page()
            
            try:
                start_time = time.time()
                print(f"Navigating to {url}...")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait a bit for dynamic content
                time.sleep(5)
                
                # Capture State
                current_url = page.url
                page_title = page.title()
                content = page.content()
                
                print(f"🔗 Current URL: {current_url}")
                print(f"📑 Page Title: {page_title}")
                
                # Check for key elements
                article_count = page.locator("article").count()
                tweet_text_count = page.locator("div[data-testid='tweetText']").count()
                print(f"🔎 Found <article>: {article_count}")
                print(f"🔎 Found tweetText: {tweet_text_count}")
                
                # Save Artifacts
                timestamp = int(time.time())
                screenshot_path = os.path.join(output_dir, f"run_{i}_{timestamp}.png")
                html_path = os.path.join(output_dir, f"run_{i}_{timestamp}.html")
                
                page.screenshot(path=screenshot_path)
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    
                print(f"📸 Screenshot saved: {os.path.basename(screenshot_path)}")
                print(f"💾 HTML saved: {os.path.basename(html_path)}")
                
            except Exception as e:
                print(f"❌ Error during run {i}: {e}")
            finally:
                page.close()
                
        browser.close()
    print("\n✅ Diagnosis complete. Please check the output directory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnose URL loading issues.")
    parser.add_argument("url", help="The URL to diagnose")
    parser.add_argument("--times", type=int, default=3, help="Number of times to repeat")
    parser.add_argument("--cookies", default="input/cookies.txt", help="Path to cookies")
    args = parser.parse_args()
    
    diagnose(args.url, args.times, args.cookies)
