"""
Cache Management CLI

Usage:
    python -m semantic.cache_cli stats
    python -m semantic.cache_cli list
    python -m semantic.cache_cli invalidate <file>
    python -m semantic.cache_cli clear
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from semantic.signal_cache import SignalCache


def run_stats(cache_dir: Path) -> None:
    """Print cache statistics."""
    cache = SignalCache(cache_dir)
    stats = cache.get_cache_stats()

    size_bytes = stats['total_size_bytes']
    if size_bytes >= 1024 * 1024:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes} B"

    print(f"Cache directory: {cache_dir}")
    print(f"Indexed files:   {stats['indexed_files']}")
    print(f"Cache size:      {size_str}")
    if stats['hits'] + stats['misses'] > 0:
        print(f"Hit rate:        {stats['hit_rate']:.1f}%")


def run_list(cache_dir: Path) -> None:
    """List all cached entries in a table."""
    cache = SignalCache(cache_dir)
    index = cache.load_index()

    if not index:
        print("No cached entries.")
        return

    col_file = max(len("File"), max(len(k) for k in index))
    col_file = min(col_file, 60)

    header_file = "File".ljust(col_file)
    header_date = "Cached At".ljust(27)
    header_size = "Size"
    print(f"{header_file}  {header_date}  {header_size}")
    print(f"{'-' * col_file}  {'-' * 27}  {'-' * 6}")

    for file_key, entry in sorted(index.items()):
        cached_at_raw = entry.get('cached_at', '')
        try:
            dt = datetime.fromisoformat(cached_at_raw)
            cached_at = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except (ValueError, TypeError):
            cached_at = cached_at_raw

        signal_file = Path(entry.get('signal_file', ''))
        if signal_file.exists():
            size_bytes = signal_file.stat().st_size
            if size_bytes >= 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes} B"
        else:
            size_str = "N/A"

        print(f"{file_key[:col_file].ljust(col_file)}  {cached_at.ljust(27)}  {size_str}")


def run_invalidate(cache_dir: Path, file_path: str) -> None:
    """Remove cache entry for a specific file."""
    cache = SignalCache(cache_dir)
    index = cache.load_index()

    if file_path not in index:
        print(f"Not cached: {file_path}")
        return

    cache.invalidate_file(Path(file_path))
    print(f"Invalidated cache for: {file_path}")


def run_clear(cache_dir: Path) -> None:
    """Clear all cache entries."""
    cache = SignalCache(cache_dir)
    index = cache.load_index()
    count = len(index)
    cache.clear_all()
    print(f"Cleared {count} cache entries.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage semantic signal cache")
    parser.add_argument('--cache-dir', default='.semantic-cache', help='Cache directory')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('stats', help='Show cache statistics')
    subparsers.add_parser('list', help='List cached entries')

    invalidate_parser = subparsers.add_parser('invalidate', help='Invalidate cache for a file')
    invalidate_parser.add_argument('file', help='File path to invalidate')

    subparsers.add_parser('clear', help='Clear all cache entries')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    cache_dir = Path(args.cache_dir)

    if args.command == 'stats':
        run_stats(cache_dir)
    elif args.command == 'list':
        run_list(cache_dir)
    elif args.command == 'invalidate':
        run_invalidate(cache_dir, args.file)
    elif args.command == 'clear':
        run_clear(cache_dir)

    return 0


if __name__ == '__main__':
    sys.exit(main())
