import os
import argparse
import sys

def deduplicate_urls(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    seen_urls = set()
    unique_lines = []
    removed_count = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        stripped = line.strip()
        # If it's a comment or empty, keep it (optional, but usually safer)
        if not stripped or stripped.startswith("#"):
            unique_lines.append(line)
            continue
        
        # Normalize URL for comparison (strip quotes/spaces)
        url_norm = stripped.strip('"\'“”')
        
        if url_norm not in seen_urls:
            seen_urls.add(url_norm)
            unique_lines.append(line)
        else:
            removed_count += 1

    if removed_count > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(unique_lines)
        print(f"Success: Removed {removed_count} duplicate URLs from {file_path}.")
    else:
        print(f"No duplicates found in {file_path}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deduplicate URLs in a text file while preserving order and comments.")
    parser.add_argument("file", nargs="?", default="input/urls.txt", help="Path to the urls file (default: input/urls.txt)")
    args = parser.parse_args()
    
    deduplicate_urls(args.file)
