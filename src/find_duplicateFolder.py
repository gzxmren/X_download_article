import os
import json
import shutil
from collections import defaultdict
from datetime import datetime
import argparse

def find_duplicates(output_dir="output", delete=False):
    # Dictionary to store entries: url -> list of {path, time, folder_name}
    records = defaultdict(list)
    
    print(f"Scanning {output_dir} for duplicates...")
    
    # 1. Scan directories
    if not os.path.exists(output_dir):
        print("Output directory not found.")
        return

    scanned_count = 0
    for entry in os.scandir(output_dir):
        if entry.is_dir():
            meta_path = os.path.join(entry.path, "meta.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        url = meta.get('url')
                        
                        # Get time priority: download_time > filesystem mtime
                        dl_time_str = meta.get('download_time')
                        if dl_time_str:
                            try:
                                timestamp = datetime.fromisoformat(dl_time_str).timestamp()
                            except ValueError:
                                timestamp = entry.stat().st_mtime
                        else:
                            timestamp = entry.stat().st_mtime
                        
                        if url:
                            records[url].append({
                                'path': entry.path,
                                'folder': entry.name,
                                'time': timestamp,
                                'time_str': dl_time_str or "Unknown"
                            })
                            scanned_count += 1
                except Exception as e:
                    print(f"Error reading {entry.name}: {e}")

    print(f"Scanned {scanned_count} folders.")
    
    # 2. Identify duplicates
    duplicates_found = 0
    bytes_saved = 0
    
    for url, entries in records.items():
        if len(entries) > 1:
            duplicates_found += 1
            # Sort by time descending (Keep the newest)
            entries.sort(key=lambda x: x['time'], reverse=True)
            
            keep = entries[0]
            remove_list = entries[1:]
            
            print(f"\n🔗 Duplicate URL: {url}")
            print(f"   ✅ KEEP: {keep['folder']} (Time: {keep['time_str']})")
            
            for item in remove_list:
                print(f"   ❌ DELETE: {item['folder']} (Time: {item['time_str']})")
                
                # Calculate size
                try:
                    size = sum(d.stat().st_size for d in os.scandir(item['path']) if d.is_file())
                    # Add assets size roughly
                    assets_path = os.path.join(item['path'], 'assets')
                    if os.path.exists(assets_path):
                        size += sum(f.stat().st_size for f in os.scandir(assets_path) if f.is_file())
                    bytes_saved += size
                except:
                    pass

                if delete:
                    try:
                        shutil.rmtree(item['path'])
                        print(f"      -> Deleted.")
                    except Exception as e:
                        print(f"      -> Failed to delete: {e}")

    if duplicates_found == 0:
        print("\n✅ No duplicates found! Your library is clean.")
    else:
        print(f"\n⚠️  Found {duplicates_found} duplicate sets.")
        if not delete:
            print("Run with --delete to remove them.")
        else:
            print(f"Cleanup complete. Reclaimed approx {bytes_saved / 1024 / 1024:.2f} MB.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find and remove duplicate articles based on URL in meta.json")
    parser.add_argument("--delete", action="store_true", help="Actually delete the duplicate folders (default is dry-run)")
    args = parser.parse_args()
    
    find_duplicates(delete=args.delete)
