#!/usr/bin/env python3
"""
Mon_PS Log Rotation Script
Fonctionne SANS sudo - Alternative à logrotate système
"""
import os
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configuration
LOG_DIR = Path("/home/Mon_ps/logs")
MAX_SIZE_MB = 10  # Rotation si > 10MB
KEEP_DAYS = 14    # Garder archives 14 jours
DRY_RUN = False   # True pour tester sans modifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
log = logging.getLogger(__name__)

def rotate_log(log_file: Path) -> bool:
    """Compresse et archive un fichier log."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive = log_file.parent / f"{log_file.stem}.{timestamp}.log.gz"

        if DRY_RUN:
            log.info(f"[DRY-RUN] Would rotate: {log_file} -> {archive}")
            return True

        # Compresser
        with open(log_file, 'rb') as f_in:
            with gzip.open(archive, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Tronquer l'original (garder le fichier pour les process qui écrivent)
        with open(log_file, 'w') as f:
            f.write(f"# Log rotated at {datetime.now().isoformat()}\n")

        log.info(f"✅ Rotated: {log_file.name} -> {archive.name}")
        return True

    except Exception as e:
        log.error(f"❌ Failed to rotate {log_file}: {e}")
        return False

def cleanup_old_archives(max_age_days: int) -> int:
    """Supprime les archives plus vieilles que max_age_days."""
    cutoff = datetime.now() - timedelta(days=max_age_days)
    deleted = 0

    for archive in LOG_DIR.glob("*.gz"):
        try:
            mtime = datetime.fromtimestamp(archive.stat().st_mtime)
            if mtime < cutoff:
                if DRY_RUN:
                    log.info(f"[DRY-RUN] Would delete: {archive}")
                else:
                    archive.unlink()
                    log.info(f"🗑️ Deleted old archive: {archive.name}")
                deleted += 1
        except Exception as e:
            log.error(f"❌ Failed to check/delete {archive}: {e}")

    return deleted

def main():
    log.info("=" * 60)
    log.info("MON_PS LOG ROTATION - START")
    log.info("=" * 60)

    if not LOG_DIR.exists():
        log.error(f"Log directory not found: {LOG_DIR}")
        return 1

    rotated = 0
    checked = 0

    # Rotation des gros fichiers
    for log_file in LOG_DIR.glob("*.log"):
        checked += 1
        size_mb = log_file.stat().st_size / (1024 * 1024)

        if size_mb > MAX_SIZE_MB:
            log.info(f"📦 {log_file.name}: {size_mb:.1f}MB > {MAX_SIZE_MB}MB threshold")
            if rotate_log(log_file):
                rotated += 1
        else:
            log.debug(f"⏭️ {log_file.name}: {size_mb:.1f}MB (OK)")

    # Nettoyage vieilles archives
    deleted = cleanup_old_archives(KEEP_DAYS)

    log.info("-" * 60)
    log.info(f"📊 SUMMARY: {checked} checked, {rotated} rotated, {deleted} deleted")
    log.info("=" * 60)

    return 0

if __name__ == "__main__":
    exit(main())
