"""
Signal Cache Management

Manages caching of extracted signals at the file level.
Enables incremental extraction by reusing signals from unchanged files.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import hashlib
from datetime import datetime, timezone


class SignalCache:
    """Manages file-level signal caching for incremental extraction"""

    def __init__(self, cache_dir: Path, max_entries: int = 100, ttl_hours: float = 24.0):
        self.cache_dir = cache_dir
        self.max_entries = max_entries
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = cache_dir / "cache_index.json"
        self.signals_dir = cache_dir / "signals"
        self.signals_dir.mkdir(parents=True, exist_ok=True)
        self._hits = 0
        self._misses = 0

    def _get_cache_key(self, file_path: Path, file_hash: str) -> str:
        """Generate cache key from file path and hash"""
        # Use both path and hash to ensure uniqueness
        key_input = f"{file_path}:{file_hash}"
        return hashlib.sha256(key_input.encode()).hexdigest()[:16]

    def _get_signal_file(self, cache_key: str) -> Path:
        """Get path to cached signal file"""
        return self.signals_dir / f"{cache_key}.json"

    def load_index(self) -> Dict[str, Any]:
        """Load cache index"""
        if not self.index_file.exists():
            return {}

        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save_index(self, index: Dict[str, Any]):
        """Save cache index"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)

    def get_cached_signals(self, file_path: Path, file_hash: str) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        Retrieve cached signals for a file.

        Returns:
            Dict with signal categories (domain_signals, concept_signals, etc.) or None if not cached
        """
        index = self.load_index()
        file_key = str(file_path)

        # Check if we have a cache entry for this file
        if file_key not in index:
            self._misses += 1
            return None

        entry = index[file_key]

        # Verify hash matches
        if entry.get('file_hash') != file_hash:
            self._misses += 1
            return None

        cache_key = entry.get('cache_key')
        if not cache_key:
            self._misses += 1
            return None

        signal_file = self._get_signal_file(cache_key)
        if not signal_file.exists():
            self._misses += 1
            return None

        # Check TTL
        if self.ttl_hours > 0:
            cached_at_str = entry.get('cached_at', '')
            if cached_at_str:
                from datetime import timedelta
                cached_at = datetime.fromisoformat(cached_at_str)
                age = datetime.now(timezone.utc) - cached_at
                if age > timedelta(hours=self.ttl_hours):
                    self._misses += 1
                    return None  # expired

        try:
            with open(signal_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._hits += 1
                return data
        except (json.JSONDecodeError, IOError):
            self._misses += 1
            return None

    def store_signals(self, file_path: Path, file_hash: str, signals: Dict[str, List[Dict[str, Any]]]):
        """
        Store signals for a file in cache.

        Args:
            file_path: Path to the source file
            file_hash: Hash of the file contents
            signals: Dict with signal categories
        """
        cache_key = self._get_cache_key(file_path, file_hash)
        signal_file = self._get_signal_file(cache_key)

        # Write signals to cache file
        with open(signal_file, 'w', encoding='utf-8') as f:
            json.dump(signals, f, indent=2)

        # Update index
        index = self.load_index()
        file_key = str(file_path)

        index[file_key] = {
            'file_hash': file_hash,
            'cache_key': cache_key,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'signal_file': str(signal_file)
        }

        # Evict oldest entries if over limit
        if self.max_entries > 0 and len(index) > self.max_entries:
            sorted_keys = sorted(index.keys(), key=lambda k: index[k].get('cached_at', ''))
            to_evict = sorted_keys[:len(index) - self.max_entries]
            for key in to_evict:
                signal_file_path = index[key].get('signal_file', '')
                if signal_file_path:
                    Path(signal_file_path).unlink(missing_ok=True)
                del index[key]
            self.save_index(index)
        else:
            self.save_index(index)

    def invalidate_file(self, file_path: Path):
        """Remove cached signals for a specific file"""
        index = self.load_index()
        file_key = str(file_path)

        if file_key in index:
            entry = index[file_key]
            cache_key = entry.get('cache_key')

            # Remove signal file
            if cache_key:
                signal_file = self._get_signal_file(cache_key)
                if signal_file.exists():
                    signal_file.unlink()

            # Remove from index
            del index[file_key]
            self.save_index(index)

    def clear_all(self):
        """Clear entire cache"""
        # Remove all signal files
        for signal_file in self.signals_dir.glob("*.json"):
            signal_file.unlink()

        # Clear index
        if self.index_file.exists():
            self.index_file.unlink()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        index = self.load_index()
        signal_files = list(self.signals_dir.glob("*.json"))
        total = self._hits + self._misses

        return {
            'indexed_files': len(index),
            'cached_signal_files': len(signal_files),
            'cache_dir': str(self.cache_dir),
            'total_size_bytes': sum(f.stat().st_size for f in signal_files),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': (self._hits / total * 100) if total > 0 else 0.0,
            'max_entries': self.max_entries,
            'ttl_hours': self.ttl_hours
        }

    def reset_stats(self) -> None:
        """Reset hit/miss counters."""
        self._hits = 0
        self._misses = 0

    def merge_signals(self, *signal_dicts: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Merge multiple signal dictionaries.

        Args:
            *signal_dicts: Variable number of signal dictionaries to merge

        Returns:
            Merged signal dictionary with all categories combined
        """
        merged = {
            'domain_signals': [],
            'concept_signals': [],
            'rule_signals': [],
            'demand_pattern_signals': []
        }

        for signals in signal_dicts:
            if not signals:
                continue

            for category in merged.keys():
                if category in signals:
                    merged[category].extend(signals[category])

        return merged
