#!/usr/bin/env python3
"""
Load test script for Real Estate AVM API.
Checks server responsiveness under concurrent load.

Usage:
    python scripts/load_test.py [--url http://localhost:8000] [--requests 100] [--concurrency 10]
"""

import argparse
import concurrent.futures
import json
import sys
import time
from dataclasses import dataclass
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Run: pip install requests")
    sys.exit(1)


@dataclass
class LatencyResult:
    status_code: int
    latency_ms: float
    success: bool
    error: Optional[str] = None


def send_request(url: str, payload: dict) -> LatencyResult:
    """Send a single valuation request and measure latency."""
    start = time.perf_counter()
    try:
        resp = requests.post(
            f"{url}/api/v2/valuation",
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"},
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return LatencyResult(
            status_code=resp.status_code,
            latency_ms=latency_ms,
            success=resp.status_code == 200,
            error=None if resp.status_code == 200 else f"HTTP {resp.status_code}",
        )
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return LatencyResult(
            status_code=0,
            latency_ms=latency_ms,
            success=False,
            error=str(e),
        )


def percentile(data: list[float], p: float) -> float:
    """Calculate percentile of a sorted list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * p / 100)
    idx = min(idx, len(sorted_data) - 1)
    return round(sorted_data[idx], 1)


def check_server_health(url: str) -> bool:
    """Check if the server is running and healthy."""
    try:
        resp = requests.get(f"{url}/docs", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def run_load_test(
    url: str,
    total_requests: int,
    concurrency: int,
    payload: dict,
) -> dict:
    """Run load test with given parameters."""
    print(f"\n{'='*60}")
    print(f"  LOAD TEST — Real Estate AVM API")
    print(f"{'='*60}")
    print(f"  Target URL:      {url}")
    print(f"  Total requests:  {total_requests}")
    print(f"  Concurrency:     {concurrency}")
    print(f"  Payload:         {payload['asset_type']} | {payload['province_city']}/{payload['district']} | {payload['area_m2']}m2")
    print(f"{'='*60}\n")

    # Check health
    print("[1/3] Checking server health...")
    if not check_server_health(url):
        print(f"ERROR: Server not reachable at {url}/docs")
        print("Make sure the server is running:")
        print(f"  uvicorn src.backend.main:app --reload")
        sys.exit(1)
    print("      Server is healthy.\n")

    # Warmup
    print("[2/3] Warmup (5 requests)...")
    for _ in range(5):
        send_request(url, payload)
    print("      Warmup done.\n")

    # Load test
    print(f"[3/3] Running {total_requests} requests with concurrency={concurrency}...")
    results: list[LatencyResult] = []
    latencies: list[float] = []

    start_time = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_request, url, payload) for _ in range(total_requests)]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            result = future.result()
            results.append(result)
            if result.success:
                latencies.append(result.latency_ms)
            if (i + 1) % 20 == 0:
                print(f"      Progress: {i+1}/{total_requests}")

    total_time = time.perf_counter() - start_time

    # Analyze results
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    errors = [r.error for r in results if not r.success and r.error]

    if latencies:
        latencies.sort()
        p50 = percentile(latencies, 50)
        p75 = percentile(latencies, 75)
        p90 = percentile(latencies, 90)
        p95 = percentile(latencies, 95)
        p99 = percentile(latencies, 99)
        min_lat = round(min(latencies), 1)
        max_lat = round(max(latencies), 1)
        avg_lat = round(sum(latencies) / len(latencies), 1)
        rps = round(total_requests / total_time, 1)
    else:
        p50 = p75 = p90 = p95 = p99 = min_lat = max_lat = avg_lat = rps = 0

    # Print results
    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Status:          {'PASS' if success_count == total_requests else 'DEGRADED'}")
    print(f"  Success rate:    {success_count}/{total_requests} ({100*success_count/total_requests:.1f}%)")
    print(f"  Total time:      {total_time:.1f}s")
    print(f"  Throughput:      {rps} req/s")
    print()
    print(f"  Latency (successful requests only):")
    print(f"    min:   {min_lat}ms")
    print(f"    avg:   {avg_lat}ms")
    print(f"    p50:   {p50}ms")
    print(f"    p75:   {p75}ms")
    print(f"    p90:   {p90}ms")
    print(f"    p95:   {p95}ms  {'✓' if p95 < 200 else '✗ ABOVE THRESHOLD (200ms)'}")
    print(f"    p99:   {p99}ms")
    print(f"    max:   {max_lat}ms")
    print()

    if errors:
        print(f"  Errors ({len(errors)}):")
        error_counts: dict[str, int] = {}
        for e in errors:
            error_counts[e] = error_counts.get(e, 0) + 1
        for err, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            print(f"    {count}x  {err}")

    print(f"{'='*60}\n")

    # Exit code: 0 if p95 < 200ms, 1 otherwise
    threshold = 200.0
    if p95 > threshold:
        print(f"FAIL: p95 latency ({p95}ms) exceeds threshold ({threshold}ms)")
        return {"status": "FAIL", "p95": p95, "threshold": threshold}
    else:
        print(f"PASS: p95 latency ({p95}ms) within threshold ({threshold}ms)")
        return {"status": "PASS", "p95": p95, "threshold": threshold}


def main():
    parser = argparse.ArgumentParser(description="Load test for Real Estate AVM API")
    parser.add_argument(
        "--url", default="http://localhost:8000",
        help="Base URL of the API server (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--requests", "-n", type=int, default=100,
        help="Total number of requests (default: 100)"
    )
    parser.add_argument(
        "--concurrency", "-c", type=int, default=10,
        help="Number of concurrent workers (default: 10)"
    )
    args = parser.parse_args()

    payload = {
        "asset_type": "APARTMENT",
        "province_city": "Hà Nội",
        "district": "Quận Cầu Giấy",
        "area_m2": 80.0,
    }

    result = run_load_test(args.url, args.requests, args.concurrency, payload)
    sys.exit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
