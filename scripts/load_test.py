#!/usr/bin/env python3
"""
Load test script for Real Estate AVM API.
Checks server responsiveness under concurrent load.

Usage:
    python scripts/load_test.py --endpoint /api/v2/pipeline --report reports/ci/prediction-latency.json
"""

import argparse
import concurrent.futures
import json
import math
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    response_body: Optional[str] = None


def send_request(url: str, endpoint: str, payload: dict) -> LatencyResult:
    """Send a single valuation request and measure latency."""
    start = time.perf_counter()
    try:
        resp = requests.post(
            f"{url.rstrip('/')}/{endpoint.lstrip('/')}",
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
            response_body=None if resp.status_code == 200 else resp.text[:500],
        )
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return LatencyResult(
            status_code=0,
            latency_ms=latency_ms,
            success=False,
            error=str(e),
            response_body=None,
        )


def percentile(data: list[float], p: float) -> float:
    """Tính percentile theo nearest-rank, ổn định cả với tập mẫu nhỏ."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = max(0, math.ceil(len(sorted_data) * p / 100) - 1)
    return round(sorted_data[idx], 1)


def check_server_health(url: str) -> bool:
    """Check if the server is running and healthy."""
    try:
        resp = requests.get(f"{url.rstrip('/')}/api/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def summarize_results(
    results: list[LatencyResult],
    total_time: float,
    threshold_ms: float,
) -> dict:
    """Tạo report machine-readable và tuyệt đối không PASS khi request lỗi."""
    successful = [result.latency_ms for result in results if result.success]
    total = len(results)
    success_count = len(successful)
    errors = Counter(
        result.error or f"HTTP {result.status_code}"
        for result in results
        if not result.success
    )
    error_samples: dict[str, str] = {}
    for result in results:
        if result.success:
            continue
        key = result.error or f"HTTP {result.status_code}"
        if key not in error_samples and result.response_body:
            error_samples[key] = result.response_body
    p95 = percentile(successful, 95) if successful else None
    all_successful = total > 0 and success_count == total
    latency_pass = p95 is not None and p95 < threshold_ms
    return {
        "status": "PASS" if all_successful and latency_pass else "FAIL",
        "total_requests": total,
        "successful_requests": success_count,
        "failed_requests": total - success_count,
        "success_rate_pct": round(100 * success_count / total, 1) if total else 0.0,
        "total_time_s": round(total_time, 3),
        "throughput_rps": round(total / total_time, 1) if total_time > 0 else 0.0,
        "threshold_ms": threshold_ms,
        "min_ms": round(min(successful), 1) if successful else None,
        "avg_ms": round(sum(successful) / len(successful), 1) if successful else None,
        "p50_ms": percentile(successful, 50) if successful else None,
        "p75_ms": percentile(successful, 75) if successful else None,
        "p90_ms": percentile(successful, 90) if successful else None,
        "p95_ms": p95,
        "p99_ms": percentile(successful, 99) if successful else None,
        "max_ms": round(max(successful), 1) if successful else None,
        "errors": dict(errors),
        "error_samples": error_samples,
    }


def run_load_test(
    url: str,
    endpoint: str,
    total_requests: int,
    concurrency: int,
    payload: dict,
    threshold_ms: float,
) -> dict:
    """Run load test with given parameters."""
    print(f"\n{'='*60}")
    print(f"  LOAD TEST — Real Estate AVM API")
    print(f"{'='*60}")
    print(f"  Target URL:      {url}")
    print(f"  Endpoint:        {endpoint}")
    print(f"  Total requests:  {total_requests}")
    print(f"  Concurrency:     {concurrency}")
    print(f"  Payload:         {payload['asset_type']} | {payload['province_city']}/{payload['district']} | {payload['area_m2']}m2")
    print(f"{'='*60}\n")

    # Check health
    print("[1/3] Checking server health...")
    if not check_server_health(url):
        print(f"ERROR: Server not reachable at {url}/api/health")
        print("Make sure the server is running:")
        print(f"  uvicorn src.backend.main:app --reload")
        return {
            "status": "FAIL",
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": total_requests,
            "success_rate_pct": 0.0,
            "threshold_ms": threshold_ms,
            "p95_ms": None,
            "errors": {"health_check_failed": 1},
        }
    print("      Server is healthy.\n")

    # Warmup
    print("[2/3] Warmup (5 requests)...")
    for _ in range(5):
        send_request(url, endpoint, payload)
    print("      Warmup done.\n")

    # Load test
    print(f"[3/3] Running {total_requests} requests with concurrency={concurrency}...")
    results: list[LatencyResult] = []

    start_time = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(send_request, url, endpoint, payload)
            for _ in range(total_requests)
        ]
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            result = future.result()
            results.append(result)
            if (i + 1) % 20 == 0:
                print(f"      Progress: {i+1}/{total_requests}")

    total_time = time.perf_counter() - start_time
    summary = summarize_results(results, total_time, threshold_ms)

    # Print results
    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Status:          {summary['status']}")
    print(f"  Success rate:    {summary['successful_requests']}/{summary['total_requests']} ({summary['success_rate_pct']:.1f}%)")
    print(f"  Total time:      {summary['total_time_s']:.3f}s")
    print(f"  Throughput:      {summary['throughput_rps']} req/s")
    print()
    print(f"  Latency (successful requests only):")
    print(f"    min:   {summary['min_ms']}ms")
    print(f"    avg:   {summary['avg_ms']}ms")
    print(f"    p50:   {summary['p50_ms']}ms")
    print(f"    p75:   {summary['p75_ms']}ms")
    print(f"    p90:   {summary['p90_ms']}ms")
    print(f"    p95:   {summary['p95_ms']}ms")
    print(f"    p99:   {summary['p99_ms']}ms")
    print(f"    max:   {summary['max_ms']}ms")
    print()

    if summary["errors"]:
        print(f"  Errors ({summary['failed_requests']}):")
        for err, count in sorted(summary["errors"].items(), key=lambda x: -x[1]):
            print(f"    {count}x  {err}")
            sample = summary.get("error_samples", {}).get(err)
            if sample:
                print(f"       sample: {sample[:240]}")

    print(f"{'='*60}\n")

    if summary["status"] == "PASS":
        print(f"PASS: 100% request thành công, p95 {summary['p95_ms']}ms < {threshold_ms}ms")
    else:
        print(f"FAIL: yêu cầu 100% thành công và p95 < {threshold_ms}ms")
    return summary


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
    parser.add_argument(
        "--endpoint", default="/api/v2/pipeline",
        help="POST endpoint (default: /api/v2/pipeline)"
    )
    parser.add_argument(
        "--threshold-ms", type=float, default=200.0,
        help="Strict p95 latency threshold in milliseconds (default: 200)"
    )
    parser.add_argument(
        "--report", type=Path,
        help="Write machine-readable JSON evidence to this path"
    )
    args = parser.parse_args()

    payload = {
        "asset_type": "APARTMENT",
        "province_city": "Hà Nội",
        "district": "Quận Cầu Giấy",
        "area_m2": 80.0,
    }

    result = run_load_test(
        args.url,
        args.endpoint,
        args.requests,
        args.concurrency,
        payload,
        args.threshold_ms,
    )
    result.update({"url": args.url, "endpoint": args.endpoint})
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.exit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
