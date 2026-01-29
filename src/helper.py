#!/usr/bin/env python3
import os
import sys
import argparse
import json
import csv
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.record_manager import RecordManager
from src.logger import logger

def cmd_sync(args):
    """Scans output directory and populates records.csv"""
    output_root = args.output
    manager = RecordManager(args.csv)
    
    print(f"🔍 Scanning {output_root} for meta.json files...")
    
    count = 0
    if os.path.exists(output_root):
        for entry in os.scandir(output_root):
            if entry.is_dir():
                meta_path = os.path.join(entry.path, "meta.json")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            
                        # Adapt meta.json fields to RecordManager fields
                        record = {
                            'url': meta.get('url'),
                            'status': 'success',
                            'title': meta.get('title'),
                            'author': meta.get('author'),
                            'date': meta.get('date'),
                            'folder_name': entry.name,
                            'source': 'sync_scan',
                            'failure_reason': ''
                        }
                        
                        if record['url']:
                            manager.save_record(record)
                            count += 1
                            if count % 10 == 0:
                                print(f"   Processed {count} records...", end='\r')
                    except Exception as e:
                        print(f"❌ Error reading {meta_path}: {e}")
    
    print(f"\n✅ Sync complete. Processed {count} valid records.")
    
    # Also scan failures.json if it exists
    fail_path = os.path.join(output_root, "failures.json")
    if os.path.exists(fail_path):
        print("🔍 Scanning failures.json...")
        try:
            with open(fail_path, 'r', encoding='utf-8') as f:
                failures = json.load(f)
                for fail in failures:
                    manager.save_record({
                        'url': fail.get('url'),
                        'status': 'failed',
                        'failure_reason': fail.get('error_msg'),
                        'source': 'sync_failures'
                    })
            print(f"   Imported {len(failures)} failure records.")
        except Exception as e:
            print(f"❌ Error reading failures.json: {e}")

def cmd_stats(args):
    """Show statistics"""
    manager = RecordManager(args.csv)
    stats = manager.get_stats()
    print("\n📊 Database Statistics")
    print("=======================")
    print(f"Total Records: {stats['total']}")
    print(f"✅ Success   : {stats['success']}")
    print(f"❌ Failed    : {stats['failed']}")
    print(f"📂 CSV Path  : {manager.csv_path}")

def cmd_export(args):
    """Export URLs to a file"""
    manager = RecordManager(args.csv)
    records = manager.load_records()
    
    # Filter?
    if args.status:
        filtered = [r['url'] for r in records.values() if r['status'] == args.status]
    else:
        filtered = [r['url'] for r in records.values()]
        
    output_file = args.file or "exported_urls.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        for url in filtered:
            f.write(f"{url}\n")
            
    print(f"✅ Exported {len(filtered)} URLs to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Helper tool for managing X-Downloader records.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Global args
    parser.add_argument("--csv", default="output/records.csv", help="Path to records CSV")
    
    # Sync
    p_sync = subparsers.add_parser("sync", help="Scan output/ directory and rebuild CSV from existing files.")
    p_sync.add_argument("--output", default="output", help="Root directory of downloaded articles")
    
    # Stats
    p_stats = subparsers.add_parser("stats", help="Show database statistics.")
    
    # Export
    p_export = subparsers.add_parser("export", help="Export URLs to a text file.")
    p_export.add_argument("--status", choices=['success', 'failed'], help="Filter by status (optional)")
    p_export.add_argument("file", nargs="?", default="exported_urls.txt", help="Output filename")
    
    args = parser.parse_args()
    
    if args.command == "sync":
        cmd_sync(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "export":
        cmd_export(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
