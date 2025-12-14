"""
Refresh Lock Manager
====================

Thread-safe per-key lock management with periodic garbage collection.

Pattern: Keep locks warm for reuse, GC stale locks periodically.

Author: Quant Engineering Team
Date: 2024-12-14
"""

import threading
import time
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class RefreshLockManager:
    """
    Manages per-key locks with soft cleanup strategy.

    Locks are kept in memory for reuse (performance).
    Stale locks (unused > 60s) cleaned every 5 minutes (GC thread).

    Memory: ~60 bytes per lock → 1000 locks = 60 KB (negligible)
    """

    def __init__(self):
        """Initialize lock manager with GC thread."""
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()  # Meta-lock for dict access

        # Track last usage for GC
        self._lock_last_used: Dict[str, float] = {}

        logger.info("RefreshLockManager initialized")

        # Start GC thread (daemon, runs every 5 min)
        self._gc_thread = threading.Thread(
            target=self._garbage_collect_loop,
            daemon=True,
            name="xfetch-lock-gc"
        )
        self._gc_thread.start()
        logger.info("Lock GC thread started (interval: 300s)")

    def get_lock(self, key: str) -> threading.Lock:
        """
        Get or create lock for key.

        Thread-safe. Updates last_used timestamp for GC.

        Args:
            key: Cache key

        Returns:
            Lock for this key (thread-safe)
        """
        thread_id = threading.get_ident()

        with self._locks_lock:
            if key not in self._locks:
                new_lock = threading.Lock()
                self._locks[key] = new_lock

                logger.info(
                    "🔑 NEW Lock created",
                    extra={
                        "key": key,
                        "thread_id": thread_id,
                        "lock_id": id(new_lock),
                        "total_locks": len(self._locks)
                    }
                )
            else:
                logger.debug(
                    "Existing lock retrieved",
                    extra={
                        "key": key,
                        "thread_id": thread_id,
                        "lock_id": id(self._locks[key]),
                        "lock_locked": self._locks[key].locked()
                    }
                )

            # Update last used timestamp (for GC)
            self._lock_last_used[key] = time.time()

            return self._locks[key]

    def cleanup_lock(self, key: str):
        """
        DEPRECATED - No longer used with soft cleanup strategy.

        Kept for backward compatibility but does nothing.
        Locks are now cleaned by periodic GC thread.

        Args:
            key: Cache key
        """
        # Intentionally empty
        # GC thread handles cleanup
        pass

    def get_active_lock_count(self) -> int:
        """
        Get number of locks currently in memory.

        Returns:
            Count of locks in memory
        """
        with self._locks_lock:
            return len(self._locks)

    def _garbage_collect_loop(self):
        """
        Background GC thread loop.

        Runs every 5 minutes, cleans locks unused > 60 seconds.
        Daemon thread - won't block process shutdown.
        """
        while True:
            try:
                time.sleep(300)  # 5 minutes
                self._garbage_collect()
            except Exception as e:
                logger.error(
                    "Lock GC error",
                    extra={"error": str(e)}
                )
                # Continue running despite errors

    def _garbage_collect(self):
        """
        Garbage collect stale locks.

        Removes locks that are:
        1. Unused for > 60 seconds
        2. Not currently held (locked)

        Thread-safe operation.
        """
        now = time.time()
        cutoff = now - 60  # 1 minute threshold

        with self._locks_lock:
            keys_to_remove = []

            for key, last_used in list(self._lock_last_used.items()):
                # Check if stale (not used recently)
                if last_used < cutoff:
                    lock = self._locks.get(key)

                    # Only remove if lock not currently held
                    if lock and not lock.locked():
                        keys_to_remove.append(key)

            # Remove stale locks
            for key in keys_to_remove:
                del self._locks[key]
                del self._lock_last_used[key]

            if keys_to_remove:
                logger.info(
                    "🗑️  Lock GC: Cleaned stale locks",
                    extra={
                        "removed": len(keys_to_remove),
                        "remaining": len(self._locks),
                        "cutoff_seconds": 60
                    }
                )
            else:
                logger.debug(
                    "Lock GC: No stale locks to clean",
                    extra={"total_locks": len(self._locks)}
                )


# Global singleton instance
refresh_lock_manager = RefreshLockManager()
