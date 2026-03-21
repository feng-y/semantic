"""
Stage-level output cache for semantic pipeline stages.

Caches full stage output (YAML dict) keyed by (stage_name, input_file_hash).
Enables skipping expensive re-computation when inputs are unchanged.
"""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class StageCache:
    """File-level cache for pipeline stage outputs"""

    def __init__(self, cache_dir: Path, ttl_hours: float = 24.0):
        self.cache_dir = cache_dir
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = cache_dir / "stage_index.json"
        self._hits = 0
        self._misses = 0

    def _cache_key(self, stage: str, input_hash: str) -> str:
        raw = f"{stage}:{input_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _cache_file(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _load_index(self) -> dict[str, Any]:
        if not self.index_file.exists():
            return {}
        try:
            with open(self.index_file, encoding='utf-8') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_index(self, index: dict[str, Any]):
        with tempfile.NamedTemporaryFile('w', dir=self.cache_dir, delete=False,
                                         suffix='.tmp', encoding='utf-8') as tmp:
            json.dump(index, tmp, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, self.index_file)

    def hash_file(self, path: Path) -> str:
        """Compute SHA256 of a file"""
        sha = hashlib.sha256()
        try:
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha.update(chunk)
            return sha.hexdigest()
        except (FileNotFoundError, PermissionError):
            return ""

    def get(self, stage: str, input_hash: str) -> dict[str, Any] | None:
        """Return cached output or None on miss/expiry"""
        index = self._load_index()
        entry_key = f"{stage}:{input_hash}"
        entry = index.get(entry_key)
        if not entry:
            self._misses += 1
            return None

        # TTL check
        if self.ttl_hours > 0:
            cached_at_str = entry.get('cached_at', '')
            if cached_at_str:
                cached_at = datetime.fromisoformat(cached_at_str)
                if datetime.now(timezone.utc) - cached_at > timedelta(hours=self.ttl_hours):
                    self._misses += 1
                    return None

        cache_file = self._cache_file(entry['cache_key'])
        if not cache_file.exists():
            self._misses += 1
            return None

        try:
            with open(cache_file, encoding='utf-8') as f:
                data = json.load(f)
            self._hits += 1
            return data
        except (OSError, json.JSONDecodeError):
            self._misses += 1
            return None

    def put(self, stage: str, input_hash: str, output: dict[str, Any]):
        """Store stage output in cache"""
        key = self._cache_key(stage, input_hash)
        cache_file = self._cache_file(key)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        index = self._load_index()
        entry_key = f"{stage}:{input_hash}"
        index[entry_key] = {
            'cache_key': key,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'stage': stage,
        }
        self._save_index(index)

    def invalidate(self, stage: str, input_hash: str):
        """Remove a specific cache entry"""
        index = self._load_index()
        entry_key = f"{stage}:{input_hash}"
        entry = index.pop(entry_key, None)
        if entry:
            self._cache_file(entry['cache_key']).unlink(missing_ok=True)
            self._save_index(index)

    def clear(self):
        """Clear all cache entries"""
        for f in self.cache_dir.glob("*.json"):
            if f != self.index_file:
                f.unlink(missing_ok=True)
        if self.index_file.exists():
            self.index_file.unlink()

    def stats(self) -> dict[str, Any]:
        index = self._load_index()
        total = self._hits + self._misses
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': (self._hits / total * 100) if total > 0 else 0.0,
            'entries': len(index),
            'cache_dir': str(self.cache_dir),
        }
