import os

class HistoryManager:
    def __init__(self, log_dir="logs"):
        self.history_file = os.path.join(log_dir, "downloaded_history.txt")
        self._ensure_file()
        self.downloaded = self._load()

    def _ensure_file(self):
        if not os.path.exists(self.history_file):
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w') as f:
                pass

    def _load(self):
        with open(self.history_file, 'r') as f:
            return set(line.strip() for line in f if line.strip())

    def exists(self, url: str) -> bool:
        return url.strip() in self.downloaded

    def add(self, url: str):
        url = url.strip()
        if url not in self.downloaded:
            self.downloaded.add(url)
            with open(self.history_file, 'a') as f:
                f.write(f"{url}\n")
