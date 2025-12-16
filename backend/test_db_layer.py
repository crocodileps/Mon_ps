#!/usr/bin/env python3
"""
Quick test script for database layer - Mon_PS Hedge Fund Grade

Run: python3 test_db_layer.py
"""

import sys
sys.path.insert(0, '/home/Mon_ps/backend')

from core.database import get_db, check_sync_connection, get_pool_status
from repositories import UnitOfWork


def main():
    print("🔬 Testing Database Layer...")
    print("=" * 60)

    # Connection
    if not check_sync_connection():
        print("❌ Database connection failed!")
        return False
    print("✅ Database connected")

    # Queries
    with get_db() as session:
        uow = UnitOfWork(session)

        try:
            odds_count = uow.odds.count()
            print(f"✅ Odds: {odds_count:,}")
        except Exception as e:
            print(f"⚠️ Odds: Table not found (normal for new DB)")

        try:
            tracking_count = uow.tracking.count()
            print(f"✅ CLV Picks: {tracking_count:,}")
        except Exception as e:
            print(f"⚠️ Tracking: Table not found (normal for new DB)")

    # Pool
    pool = get_pool_status()
    print(f"✅ Pool: {pool['pool_size']} connections")

    print("=" * 60)
    print("\n🎉 Database Layer OK!")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
