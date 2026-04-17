"""Concurrent load testing utility for the code completion API."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import requests


@dataclass
class RequestResult:
    success: bool
    status_code: int
    latency_ms: float


def run_single_request(url: str, api_key: str, payload: Dict[str, str], timeout: float) -> RequestResult:
    started = time.perf_counter()
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        return RequestResult(success=response.status_code == 200, status_code=response.status_code, latency_ms=latency_ms)
    except requests.RequestException:
        latency_ms = (time.perf_counter() - started) * 1000
        return RequestResult(success=False, status_code=0, latency_ms=latency_ms)


def summarize(results: List[RequestResult], duration_seconds: int) -> Dict[str, object]:
    latencies = [r.latency_ms for r in results]
    total = len(results)
    success = sum(1 for r in results if r.success)
    errors = total - success

    latency_stats = {
        "min": float(np.min(latencies)) if latencies else 0.0,
        "max": float(np.max(latencies)) if latencies else 0.0,
        "p50": float(np.percentile(latencies, 50)) if latencies else 0.0,
        "p95": float(np.percentile(latencies, 95)) if latencies else 0.0,
        "p99": float(np.percentile(latencies, 99)) if latencies else 0.0,
    }

    return {
        "duration_seconds": duration_seconds,
        "total_requests": total,
        "successful_requests": success,
        "failed_requests": errors,
        "error_rate": (errors / total) if total else 0.0,
        "throughput_rps": (total / duration_seconds) if duration_seconds else 0.0,
        "latency_ms": latency_stats,
    }


def run_load_test(url: str, api_key: str, workers: int, duration_seconds: int, timeout: float) -> Dict[str, object]:
    deadline = time.time() + duration_seconds
    payload = {"code": "def add(a, b):", "max_new_tokens": 32}
    futures = []
    results: List[RequestResult] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        while time.time() < deadline:
            futures.append(executor.submit(run_single_request, url, api_key, payload, timeout))

        for future in as_completed(futures):
            results.append(future.result())

    return summarize(results, duration_seconds)


def save_results(result: Dict[str, object], output_path: str) -> None:
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load test the CodeIntel completion API")
    parser.add_argument("--url", default="http://localhost:5000/api/complete")
    parser.add_argument("--api-key", default="test-key")
    parser.add_argument("--workers", type=int, default=10, choices=[10, 50, 100])
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", default="load_testing/results/load_test_results.json")
    args = parser.parse_args()

    result = run_load_test(
        url=args.url,
        api_key=args.api_key,
        workers=args.workers,
        duration_seconds=args.duration,
        timeout=args.timeout,
    )
    save_results(result, args.output)

    print(json.dumps(result, indent=2))
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
