#!/usr/bin/env python3
"""
X-FETCH STAMPEDE PREVENTION - FINAL CERTIFICATION TEST
======================================================

CRITICAL: This test MUST be run INSIDE the backend container for accurate results.

Test Strategy:
1. Prime cache with SHORT TTL (payload: 5s, Redis: 120s)
2. Wait for cache to become STALE (6s wait)
3. Launch 100 TRULY CONCURRENT requests
4. Validate double re-check pattern

Expected Results (A++ Certification):
- Stampede prevention: compute_calls ≤ 2
- Background refresh: compute_calls ≥ 1
- Stale detection: xfetch_triggers ≥ 10
- Zero latency: P99 < 100ms for cached responses

Run from HOST:
    docker exec monps_backend python3 /tmp/test_stampede_FINAL_CERTIFICATION.py

Run from CONTAINER:
    cd /app && python3 /tmp/test_stampede_FINAL_CERTIFICATION.py
"""

import requests
import time
import redis
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys

# ══════════════════════════════════════════════════════════════
# CONFIGURATION - CONTAINER ENVIRONMENT
# ══════════════════════════════════════════════════════════════
API_URL = "http://localhost:8000/api/v1/brain/calculate"
METRICS_URL = "http://localhost:8000/api/v1/brain/metrics/cache"
RESET_URL = "http://localhost:8000/api/v1/brain/metrics/cache/reset"

REDIS_HOST = "monps_redis"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = "monps_redis_dev_password_change_in_prod"

# ══════════════════════════════════════════════════════════════
# TEST PARAMETERS
# ══════════════════════════════════════════════════════════════
N_CONCURRENT = 100

# CRITICAL: Payload TTL < Redis TTL → Cache becomes STALE but not EXPIRED
CACHE_TTL_SHORT = 5      # Payload TTL: 5 seconds (SmartCache staleness check)
REDIS_TTL_EXTENDED = 120  # Redis TTL: 2 minutes (keeps key alive)
WAIT_FOR_STALE = 6       # Wait 6s → Cache STALE (age=6s > ttl=5s) but EXISTS


def print_header(title):
    """Print formatted section header."""
    print(f"\n{'═' * 70}")
    print(f"{title:^70}")
    print(f"{'═' * 70}")


def get_redis_client():
    """Connect to Redis."""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=False
    )


def get_cache_key():
    """Get cache key for test match."""
    home = "ManCity"
    away = "Liverpool"
    match_id = f"m_{home.lower()}_vs_{away.lower()}"
    key = f"monps:prod:v1:pred:{match_id}:default"
    return key, home, away


def reset_metrics():
    """Reset cache metrics."""
    try:
        response = requests.post(RESET_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Metrics reset successfully")
            return True
        else:
            print(f"⚠️  Metrics reset failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"⚠️  Metrics reset failed: {e}")
    return False


def prime_cache_with_short_ttl(redis_client, cache_key, home, away):
    """
    Prime cache with SHORT payload TTL to force stale quickly.

    Strategy:
    - Payload TTL: SHORT (5s) → SmartCache detects as STALE after 6s
    - Redis TTL: EXTENDED (120s) → Key stays in Redis (not EXPIRED)
    - Result: Cache is STALE but EXISTS ✅
    """
    print(f"\n🔧 Priming cache with SHORT payload TTL...")
    print(f"   Payload TTL: {CACHE_TTL_SHORT}s (becomes stale)")
    print(f"   Redis TTL: {REDIS_TTL_EXTENDED}s (keeps key alive)")
    print(f"   Strategy: STALE but not EXPIRED ✅")

    # Create minimal prediction payload
    prediction = {
        "status": "success",
        "markets": [
            {"market": "1X2", "proba_home": 0.50, "proba_draw": 0.25, "proba_away": 0.25}
        ],
        "calculation_time": 0.05,
        "brain_version": "test-v1.0"
    }

    # Cache payload with SHORT TTL
    now = time.time()
    payload = {
        "value": prediction,
        "ttl": CACHE_TTL_SHORT,     # ← SmartCache checks THIS
        "created_at": now
    }

    try:
        # Store with EXTENDED Redis TTL
        redis_client.setex(
            cache_key,
            REDIS_TTL_EXTENDED,     # ← Redis keeps key alive
            json.dumps(payload)
        )

        print(f"\n✅ Cache primed successfully:")
        print(f"   Key: {cache_key[:55]}...")
        print(f"   Payload TTL: {CACHE_TTL_SHORT}s")
        print(f"   Redis TTL: {REDIS_TTL_EXTENDED}s")
        print(f"   Created: {datetime.fromtimestamp(now).strftime('%H:%M:%S')}")

        # Verify
        exists = redis_client.exists(cache_key)
        print(f"   Verified: {'EXISTS ✅' if exists else 'NOT FOUND ❌'}")

        return True

    except Exception as e:
        print(f"❌ Failed to prime cache: {e}")
        return False


def wait_for_stale():
    """Wait for cache to become stale."""
    print(f"\n⏳ Waiting {WAIT_FOR_STALE}s for cache to become STALE...")

    for i in range(WAIT_FOR_STALE):
        time.sleep(1)
        print(f"   {i+1}s... ", end="", flush=True)

    print("\n✅ Cache should now be STALE")


def verify_cache_state(redis_client, cache_key):
    """Verify cache is stale before concurrent requests."""
    print(f"\n🔍 Verifying cache state...")

    try:
        cached = redis_client.get(cache_key)
        if cached:
            payload = json.loads(cached)
            age = time.time() - payload['created_at']
            ttl = payload['ttl']
            is_stale = age >= ttl

            print(f"   Age: {age:.1f}s")
            print(f"   TTL: {ttl}s")
            print(f"   Status: {'STALE ✅' if is_stale else 'FRESH ❌'}")

            if not is_stale:
                print(f"⚠️  Cache not stale yet! Waiting 2s more...")
                time.sleep(2)
                return verify_cache_state(redis_client, cache_key)

            return True
        else:
            print(f"❌ Cache EXPIRED (key deleted by Redis)")
            return False

    except Exception as e:
        print(f"⚠️  Verification failed: {e}")
        return False


def make_request(i, home, away):
    """Make single request to API."""
    try:
        from datetime import timezone
        payload = {
            "home_team": home,
            "away_team": away,
            "match_date": datetime.now(timezone.utc).date().isoformat()
        }

        response = requests.post(
            API_URL,
            json=payload,
            timeout=10
        )

        return {
            "request_id": i,
            "status_code": response.status_code,
            "latency_ms": response.elapsed.total_seconds() * 1000
        }

    except Exception as e:
        return {
            "request_id": i,
            "status_code": 0,
            "error": str(e)
        }


def launch_concurrent_requests(n, home, away):
    """Launch N concurrent requests."""
    print(f"\n🚀 Launching {n} CONCURRENT requests on STALE cache...")
    start_time = time.time()

    results = []
    with ThreadPoolExecutor(max_workers=n) as executor:
        futures = [
            executor.submit(make_request, i, home, away)
            for i in range(n)
        ]

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    duration = time.time() - start_time

    print(f"✅ {len(results)} requests completed in {duration:.2f}s")

    # Calculate stats
    success = sum(1 for r in results if r["status_code"] == 200)
    latencies = [r["latency_ms"] for r in results if "latency_ms" in r]

    if latencies:
        latencies.sort()
        p50 = latencies[len(latencies)//2]
        p99 = latencies[int(len(latencies)*0.99)]
        avg = sum(latencies) / len(latencies)

        print(f"\n📊 Request Statistics:")
        print(f"   Success: {success}/{n}")
        print(f"   Latency P50: {p50:.2f}ms")
        print(f"   Latency P99: {p99:.2f}ms")
        print(f"   Latency AVG: {avg:.2f}ms")

    return results, latencies


def get_metrics():
    """Get cache metrics."""
    try:
        response = requests.get(METRICS_URL, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"❌ Failed to get metrics: {e}")
    return None


def validate_certification(metrics, latencies):
    """Validate A++ certification criteria."""
    print_header("FINAL CERTIFICATION VALIDATION")

    if not metrics:
        print("❌ No metrics available")
        return False

    compute_calls = metrics.get("compute_calls", 0)
    xfetch_triggers = metrics.get("xfetch_triggers", 0)
    lock_contention = metrics.get("xfetch_lock_contention_total", 0)

    print(f"\n📊 Key Metrics:")
    print(f"   compute_calls: {compute_calls}")
    print(f"   xfetch_triggers: {xfetch_triggers}")
    print(f"   lock_contention: {lock_contention}")

    # Validation criteria
    print(f"\n🎯 A++ Certification Criteria:")

    # Test 1: Stampede Prevention
    stampede_pass = compute_calls <= 2
    print(f"   1. Stampede Prevention (compute_calls ≤ 2): ", end="")
    print(f"{'✅ PASS' if stampede_pass else '❌ FAIL'} ({compute_calls})")

    # Test 2: Background refresh triggered
    refresh_pass = compute_calls >= 1
    print(f"   2. Background Refresh (compute_calls ≥ 1): ", end="")
    print(f"{'✅ PASS' if refresh_pass else '❌ FAIL'} ({compute_calls})")

    # Test 3: Stale cache detected
    triggers_pass = xfetch_triggers >= 10
    print(f"   3. Stale Cache Detected (triggers ≥ 10): ", end="")
    print(f"{'✅ PASS' if triggers_pass else '❌ FAIL'} ({xfetch_triggers})")

    # Test 4: Zero latency (cached responses)
    if latencies:
        p99 = latencies[int(len(latencies)*0.99)]
        latency_pass = p99 < 100  # <100ms for cached responses
        print(f"   4. Zero Latency (P99 < 100ms): ", end="")
        print(f"{'✅ PASS' if latency_pass else '❌ FAIL'} ({p99:.2f}ms)")
    else:
        latency_pass = False
        print(f"   4. Zero Latency: ❌ FAIL (no data)")

    # Overall
    all_pass = stampede_pass and refresh_pass and triggers_pass and latency_pass

    print(f"\n{'═' * 70}")
    if all_pass:
        print(f"{'🏆 A++ PERFECTIONNISTE - CERTIFIED':^70}")
        print(f"{'Pattern: Double Re-Check (Belt + Suspenders)':^70}")
        print(f"{'Production Ready ✅':^70}")
    else:
        print(f"{'❌ CERTIFICATION FAILED':^70}")
    print(f"{'═' * 70}")

    return all_pass


def main():
    """Main test execution."""
    print_header("X-FETCH STAMPEDE PREVENTION - FINAL CERTIFICATION")
    print(f"Pattern: Double Re-Check (Belt + Suspenders)")
    print(f"Target: A++ Perfectionniste Grade")

    # Get cache key
    cache_key, home, away = get_cache_key()
    print(f"\n🎯 Test Parameters:")
    print(f"   Teams: {home} vs {away}")
    print(f"   Cache Key: {cache_key[:50]}...")
    print(f"   Concurrent Requests: {N_CONCURRENT}")
    print(f"   Payload TTL: {CACHE_TTL_SHORT}s (SHORT - becomes stale)")
    print(f"   Redis TTL: {REDIS_TTL_EXTENDED}s (EXTENDED - keeps key)")
    print(f"   Wait Time: {WAIT_FOR_STALE}s (cache STALE but not EXPIRED)")

    # Connect to Redis
    print(f"\n🔌 Connecting to Redis...")
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        print(f"✅ Redis connected")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

    # Step 1: Reset metrics
    reset_metrics()

    # Step 2: Prime cache with SHORT TTL
    if not prime_cache_with_short_ttl(redis_client, cache_key, home, away):
        return False

    # Step 3: Wait for cache to become STALE
    wait_for_stale()

    # Step 4: Verify cache is stale
    if not verify_cache_state(redis_client, cache_key):
        return False

    # Step 5: Launch concurrent requests
    results, latencies = launch_concurrent_requests(N_CONCURRENT, home, away)

    # Step 6: Wait for background workers to complete
    print(f"\n⏳ Waiting 3s for background workers to complete...")
    time.sleep(3)

    # Step 7: Get metrics
    metrics = get_metrics()

    # Step 8: Validate certification
    success = validate_certification(metrics, latencies)

    # Final status
    print(f"\n{'═' * 70}")
    if success:
        print(f"🎉 CERTIFICATION: A++ PERFECTIONNISTE ACHIEVED!")
        print(f"   X-Fetch Stampede Prevention: PRODUCTION READY ✅")
        print(f"   Double Re-Check Pattern: VERIFIED ✅")
        print(f"   Institutional Grade: CERTIFIED ✅")
    else:
        print(f"📊 CERTIFICATION: Additional tuning needed")
        print(f"   Review metrics and adjust thresholds")
    print(f"{'═' * 70}\n")

    return success


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
