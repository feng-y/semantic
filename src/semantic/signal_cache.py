"""
Signal Cache Management

Manages caching of extracted signals at the file level.
Enables incremental extraction by reusing signals from unchanged files.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import hashlib
import os
import tempfile
from datetime import datetime, timezone, timedelta

try:
    from .signal_schema import validate_signals
except ImportError:
    from signal_schema import validate_signals


class SignalCache:
    """Manages file-level signal caching for incremental extraction"""

    def __init__(self, cache_dir: Path, max_entries: int = 100, ttl_hours: float = 24.0, compress: bool = False):
        self.cache_dir = cache_dir
        self.max_entries = max_entries
        self.ttl_hours = ttl_hours
        self.compress = compress
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
        ext = ".json.gz" if self.compress else ".json"
        return self.signals_dir / f"{cache_key}{ext}"

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
        """Save cache index (atomic write)"""
        with tempfile.NamedTemporaryFile('w', dir=self.cache_dir, delete=False,
                                         suffix='.tmp', encoding='utf-8') as tmp:
            json.dump(index, tmp, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, self.index_file)

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
                cached_at = datetime.fromisoformat(cached_at_str)
                age = datetime.now(timezone.utc) - cached_at
                if age > timedelta(hours=self.ttl_hours):
                    self._misses += 1
                    return None  # expired

        try:
            if self.compress:
                import gzip
                with gzip.open(signal_file, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
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
        is_valid, errors = validate_signals(signals)
        if not is_valid:
            raise ValueError(f"Invalid signals schema: {'; '.join(errors)}")

        cache_key = self._get_cache_key(file_path, file_hash)
        signal_file = self._get_signal_file(cache_key)

        # Write signals to cache file
        if self.compress:
            import gzip
            with gzip.open(signal_file, 'wt', encoding='utf-8') as f:
                json.dump(signals, f)
        else:
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
        for signal_file in self.signals_dir.glob("*.json.gz"):
            signal_file.unlink()

        # Clear index
        if self.index_file.exists():
            self.index_file.unlink()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        index = self.load_index()
        signal_files = list(self.signals_dir.glob("*.json")) + list(self.signals_dir.glob("*.json.gz"))
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
            'ttl_hours': self.ttl_hours,
            'compressed': self.compress
        }

    def reset_stats(self) -> None:
        """Reset hit/miss counters."""
        self._hits = 0
        self._misses = 0

    def validate_consistency(self, repair: bool = False) -> Dict[str, Any]:
        """
        Validate consistency between cache index and signal files on disk.

        Detects:
        - Orphaned signal files (file on disk but not in index)
        - Missing signal files (in index but file missing on disk)
        - Hash mismatches (index entry exists but signal file is unreadable/corrupt)

        Args:
            repair: If True, automatically fix issues (remove orphans, remove broken index entries)

        Returns:
            Dict with keys:
                'orphaned_files': list of Path (signal files not in index)
                'missing_files': list of str (index keys with no signal file)
                'corrupt_files': list of str (index keys with unreadable signal file)
                'repaired': bool (True if repair=True and changes were made)
                'is_consistent': bool (True if no issues found)
        """
        import gzip as _gzip

        index = self.load_index()

        # Build set of signal file paths referenced by the index
        indexed_signal_files = set()
        for entry in index.values():
            sf = entry.get('signal_file', '')
            if sf:
                indexed_signal_files.add(Path(sf))

        # Find orphaned files: on disk but not referenced by index
        disk_files = list(self.signals_dir.glob("*.json")) + list(self.signals_dir.glob("*.json.gz"))
        orphaned_files = [f for f in disk_files if f not in indexed_signal_files]

        # Find missing and corrupt files
        missing_files = []
        corrupt_files = []
        for file_key, entry in index.items():
            sf = entry.get('signal_file', '')
            if not sf:
                missing_files.append(file_key)
                continue
            signal_path = Path(sf)
            if not signal_path.exists():
                missing_files.append(file_key)
                continue
            try:
                if signal_path.suffix == '.gz':
                    with _gzip.open(signal_path, 'rt', encoding='utf-8') as f:
                        json.load(f)
                else:
                    with open(signal_path, 'r', encoding='utf-8') as f:
                        json.load(f)
            except Exception:
                corrupt_files.append(file_key)

        is_consistent = not orphaned_files and not missing_files and not corrupt_files
        repaired = False

        if repair and not is_consistent:
            for f in orphaned_files:
                f.unlink(missing_ok=True)
            broken_keys = set(missing_files) | set(corrupt_files)
            for key in broken_keys:
                index.pop(key, None)
            self.save_index(index)
            repaired = True

        return {
            'orphaned_files': orphaned_files,
            'missing_files': missing_files,
            'corrupt_files': corrupt_files,
            'repaired': repaired,
            'is_consistent': is_consistent,
        }

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
