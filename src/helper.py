#!/usr/bin/env python3
import os
import sys
import argparse
import json
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.record_manager import RecordManager
from src.indexer import IndexGenerator
from src.logger import logger

def get_real_html_path(folder_path):
    """Finds the actual HTML file in the folder (Relative path)."""
    folder_name = os.path.basename(folder_path)
    # Tier 1: Exact match | Tier 2: Legacy | Tier 3: Scan
    matches = [f"{folder_name}.html", "article.html"]
    for m in matches:
        if os.path.isfile(os.path.join(folder_path, m)):
            return f"{folder_name}/{m}"
    try:
        with os.scandir(folder_path) as it:
            for entry in it:
                if entry.is_file() and entry.name.lower().endswith('.html'):
                    return f"{folder_name}/{entry.name}"
    except: pass
    return ""

def cmd_sync(args):
    """Scans output directory and updates records.csv efficiently."""
    output_root = args.output
    manager = RecordManager(args.csv)
    
    print(f"🔍 Scanning {output_root} for meta.json files...")
    
    existing_folders = set()
    changes_made = False
    
    if os.path.exists(output_root):
        for entry in os.scandir(output_root):
            if entry.is_dir():
                meta_path = os.path.join(entry.path, "meta.json")
                if os.path.exists(meta_path):
                    existing_folders.add(entry.name)
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                        
                        if not meta.get('url'): continue
                        
                        # Use RecordManager's built-in normalization (Staff way)
                        record_data = meta.copy()
                        record_data.update({
                            'status': 'success',
                            'folder_name': entry.name,
                            'local_path': get_real_html_path(entry.path),
                            'source': 'sync_scan'
                        })
                        manager.update_record_memory(record_data)
                        changes_made = True
                    except Exception as e:
                        print(f"❌ Error reading {meta_path}: {e}")

    # Cleanup orphan records
    print("🧹 Cleaning up records with missing folders...")
    to_remove = [url for url, rec in manager._records.items() 
                 if rec.get('status') == 'success' and rec.get('folder_name') not in existing_folders]
    
    for url in to_remove:
        print(f"   Removing orphan: {url}")
        del manager._records[url]
        changes_made = True
    
    if changes_made:
        manager._commit()
        print(f"✅ Database updated.")
    
    # Sync failures.json
    fail_path = os.path.join(output_root, "failures.json")
    if os.path.exists(fail_path):
        print("🔍 Syncing failures.json...")
        try:
            with open(fail_path, 'r', encoding='utf-8') as f:
                failures = json.load(f)
                for fail in failures:
                    url = fail.get('url')
                    if url and url not in manager._records:
                        manager.update_record_memory({
                            'url': url, 'status': 'failed',
                            'failure_reason': fail.get('error_msg', 'Unknown'),
                            'source': 'sync_failures'
                        })
                        changes_made = True
            if changes_made: manager._commit()
        except: pass

    # Always trigger index regeneration
    print("📊 Regenerating index.html...")
    IndexGenerator(output_root).generate(records=manager.get_all_records())
    print("✨ Sync complete.")

def cmd_stats(args):
    manager = RecordManager(args.csv)
    s = manager.get_stats()
    print(f"\n📊 Stats: Total {s['total']} | Success {s['success']} | Failed {s['failed']}")

def cmd_export(args):
    manager = RecordManager(args.csv)
    filtered = [r['url'] for r in manager._records.values() if not args.status or r['status'] == args.status]
    with open(args.file, 'w', encoding='utf-8') as f:
        for url in filtered: f.write(f"{url}\n")
    print(f"✅ Exported {len(filtered)} URLs to {args.file}")

def main():
    parser = argparse.ArgumentParser(description="Helper tool for X-Downloader.")
    parser.add_argument("--csv", default="output/records.csv", help="Database CSV path")
    sub = parser.add_subparsers(dest="command")
    
    p_sync = sub.add_parser("sync", help="Sync CSV with disk files & rebuild index")
    p_sync.add_argument("--output", default="output", help="Output directory")
    
    sub.add_parser("stats", help="Show download stats")
    
    p_exp = sub.add_parser("export", help="Export URLs to text file")
    p_exp.add_argument("--status", choices=['success', 'failed'])
    p_exp.add_argument("file", nargs="?", default="exported_urls.txt")
    
    args = parser.parse_args()
    if args.command == "sync": cmd_sync(args)
    elif args.command == "stats": cmd_stats(args)
    elif args.command == "export": cmd_export(args)
    else: parser.print_help()

if __name__ == "__main__":
    main()
