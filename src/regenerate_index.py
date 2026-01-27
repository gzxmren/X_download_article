import os
import argparse
import sys

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.indexer import IndexGenerator

def main():
    parser = argparse.ArgumentParser(description="Regenerate index.html from existing downloads.")
    parser.add_argument("--output", "-o", default="output", help="Output directory containing downloaded articles")
    parser.add_argument("--input", "-i", default="input/urls.txt", help="Input file with URLs for sorting order")
    args = parser.parse_args()

    # Read URLs for sorting if available
    urls = []
    if os.path.isfile(args.input):
        print(f"Reading sort order from: {args.input}")
        with open(args.input, 'r') as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    urls.append(stripped.strip('"\'“”'))
    else:
        print(f"Warning: Input file {args.input} not found. Index will be sorted by date.")

    print(f"Regenerating index for {args.output}...")
    indexer = IndexGenerator(args.output, ordered_urls=urls)
    indexer.generate()
    print("Done.")

if __name__ == "__main__":
    main()

