"""Kiểm thử release gate hiệu năng API."""

from scripts.load_test import LatencyResult, percentile, summarize_results


def test_percentile_uses_nearest_rank_for_small_samples():
    assert percentile([10.0, 20.0], 95) == 20.0
    assert percentile([40.0, 10.0, 30.0, 20.0], 50) == 20.0


def test_summary_fails_when_every_request_fails():
    results = [LatencyResult(500, 12.0, False, "HTTP 500") for _ in range(3)]

    summary = summarize_results(results, total_time=0.2, threshold_ms=200.0)

    assert summary["status"] == "FAIL"
    assert summary["success_rate_pct"] == 0.0
    assert summary["p95_ms"] is None


def test_summary_enforces_success_rate_and_strict_latency_threshold():
    degraded = [
        LatencyResult(200, 40.0, True),
        LatencyResult(503, 20.0, False, "HTTP 503"),
    ]
    at_threshold = [LatencyResult(200, 200.0, True)]

    assert summarize_results(degraded, 0.1, 200.0)["status"] == "FAIL"
    assert summarize_results(at_threshold, 0.1, 200.0)["status"] == "FAIL"
