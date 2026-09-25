"""
Deduplication engine for the Discovery Engine.

Uses SHA-256 hashing to detect and prevent duplicate content
across crawl runs and data sources.

Usage:
    from crawlers.dedup import DedupEngine
    dedup = DedupEngine()
    is_dup = dedup.is_duplicate("reddit|user123|2024-01-01|some content...")
"""

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DedupEngine:
    """
    SHA-256 based deduplication engine.

    Maintains a set of content hashes to detect duplicates. The hash is
    computed from a composite key: (source + author_id + timestamp + content_snippet).

    The hash set can optionally be persisted to disk for cross-session dedup.
    """

    def __init__(self, persist_path: str | Path | None = None):
        """
        Initialize the dedup engine.

        Args:
            persist_path: Optional path to a JSON file for persisting
                          hashes across sessions. If None, dedup is
                          in-memory only (within a single crawl run).
        """
        self._hashes: set[str] = set()
        self._persist_path = Path(persist_path) if persist_path else None

        if self._persist_path and self._persist_path.exists():
            self._load_hashes()

    def compute_hash(self, key: str) -> str:
        """
        Compute SHA-256 hash of the dedup key.

        Args:
            key: Composite string in format "source|author|timestamp|content_snippet"

        Returns:
            Hex digest of the SHA-256 hash
        """
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def is_duplicate(self, key: str) -> bool:
        """
        Check if a key has been seen before.

        If the key is new, it is added to the hash set and returns False.
        If the key has been seen, returns True.

        Args:
            key: Composite dedup key

        Returns:
            True if duplicate, False if new
        """
        hash_val = self.compute_hash(key)

        if hash_val in self._hashes:
            return True

        self._hashes.add(hash_val)
        return False

    def add(self, key: str) -> None:
        """
        Add a key to the hash set without checking for duplicates.

        Args:
            key: Composite dedup key
        """
        hash_val = self.compute_hash(key)
        self._hashes.add(hash_val)

    def contains(self, key: str) -> bool:
        """
        Check if a key exists without adding it.

        Args:
            key: Composite dedup key

        Returns:
            True if the key exists in the hash set
        """
        hash_val = self.compute_hash(key)
        return hash_val in self._hashes

    @property
    def count(self) -> int:
        """Return the number of unique hashes stored."""
        return len(self._hashes)

    def save(self) -> None:
        """Persist the hash set to disk."""
        if self._persist_path is None:
            logger.warning("No persist path configured; skipping save")
            return

        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persist_path, "w", encoding="utf-8") as f:
            json.dump(list(self._hashes), f)

        logger.info("Saved %d hashes to %s", len(self._hashes), self._persist_path)

    def _load_hashes(self) -> None:
        """Load hash set from disk."""
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                hashes = json.load(f)
                self._hashes = set(hashes)
            logger.info(
                "Loaded %d hashes from %s",
                len(self._hashes),
                self._persist_path,
            )
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning("Failed to load hashes: %s", e)
            self._hashes = set()

    def clear(self) -> None:
        """Clear all stored hashes."""
        self._hashes.clear()
