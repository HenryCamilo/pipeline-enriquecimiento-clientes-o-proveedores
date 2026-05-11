"""
File-level cache using SHA256 hash of content + file size.
Caches: extracted text, OCR per page, entities, match result, useful pages.
Stored as JSON files under a configurable cache directory.
"""

import hashlib
import json
import os
from typing import Any


DEFAULT_CACHE_DIR = "cache"


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    stat = os.stat(path)
    h.update(str(stat.st_size).encode())
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


class CacheManager:
    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _cache_path(self, file_hash: str) -> str:
        return os.path.join(self.cache_dir, f"{file_hash}.json")

    def get_hash(self, path: str) -> str:
        return _file_hash(path)

    def load(self, file_hash: str) -> dict | None:
        p = self._cache_path(file_hash)
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, file_hash: str, data: dict) -> None:
        p = self._cache_path(file_hash)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def has(self, file_hash: str) -> bool:
        return os.path.exists(self._cache_path(file_hash))
