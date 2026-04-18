"""Monitoring utilities for API performance and cost analysis."""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from functools import wraps
from typing import Any, Callable, Deque, Dict, Optional

import boto3
import numpy as np

logger = logging.getLogger(__name__)


class MonitoringSystem:
    """Tracks latency, throughput, and CloudWatch metrics."""

    def __init__(self, namespace: str = "CodeIntelAPI", max_samples: int = 10000) -> None:
        self.namespace = namespace
        self._latencies: Deque[float] = deque(maxlen=max_samples)
        self._success = 0
        self._errors = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._started_at = time.time()
        self._cost_per_1000 = float(os.getenv("COST_PER_1000_REQUESTS_USD", "0.25"))
        self._enable_cloudwatch = os.getenv("ENABLE_CLOUDWATCH", "false").lower() == "true"
        self._cloudwatch = boto3.client("cloudwatch") if self._enable_cloudwatch else None

    def record_request(
        self,
        latency_ms: float,
        success: bool,
        cached: Optional[bool] = None,
        request_count: int = 1,
    ) -> None:
        self._latencies.append(max(latency_ms, 0.0))
        increment = max(int(request_count), 1)
        if success:
            self._success += increment
        else:
            self._errors += increment

        if cached is True:
            self._cache_hits += increment
        elif cached is False:
            self._cache_misses += increment

    def _percentile(self, value: int) -> float:
        if not self._latencies:
            return 0.0
        return float(np.percentile(list(self._latencies), value))

    def _throughput(self) -> float:
        elapsed = max(time.time() - self._started_at, 1e-6)
        return (self._success + self._errors) / elapsed

    def _requests_per_minute(self) -> float:
        return self._throughput() * 60.0

    def _cost_usd(self) -> float:
        total_requests = self._success + self._errors
        return (total_requests / 1000.0) * self._cost_per_1000

    def _cache_hit_rate(self) -> float:
        total = self._cache_hits + self._cache_misses
        return (self._cache_hits / total) if total else 0.0

    def _cache_miss_rate(self) -> float:
        total = self._cache_hits + self._cache_misses
        return (self._cache_misses / total) if total else 0.0

    def get_metrics(self) -> Dict[str, Any]:
        total_requests = self._success + self._errors
        return {
            "total_requests": total_requests,
            "success_requests": self._success,
            "error_requests": self._errors,
            "error_rate": (self._errors / total_requests) if total_requests else 0.0,
            "throughput_rps": self._throughput(),
            "requests_per_minute": self._requests_per_minute(),
            "latency_ms": {
                "p50": self._percentile(50),
                "p95": self._percentile(95),
                "p99": self._percentile(99),
                "min": min(self._latencies) if self._latencies else 0.0,
                "max": max(self._latencies) if self._latencies else 0.0,
                "avg": (sum(self._latencies) / len(self._latencies)) if self._latencies else 0.0,
            },
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self._cache_hit_rate(),
            "cache_miss_rate": self._cache_miss_rate(),
            "estimated_cost_usd": self._cost_usd(),
            "estimated_cost_per_1000_requests_usd": self._cost_per_1000,
        }

    def publish_cloudwatch_metrics(self) -> None:
        if self._cloudwatch is None:
            logger.debug("CloudWatch publishing disabled")
            return

        metrics = self.get_metrics()
        try:
            self._cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        "MetricName": "RequestCount",
                        "Unit": "Count",
                        "Value": metrics["total_requests"],
                    },
                    {
                        "MetricName": "ErrorRate",
                        "Unit": "Percent",
                        "Value": metrics["error_rate"] * 100,
                    },
                    {
                        "MetricName": "LatencyP50",
                        "Unit": "Milliseconds",
                        "Value": metrics["latency_ms"]["p50"],
                    },
                    {
                        "MetricName": "LatencyP95",
                        "Unit": "Milliseconds",
                        "Value": metrics["latency_ms"]["p95"],
                    },
                    {
                        "MetricName": "LatencyP99",
                        "Unit": "Milliseconds",
                        "Value": metrics["latency_ms"]["p99"],
                    },
                    {
                        "MetricName": "LatencyAvg",
                        "Unit": "Milliseconds",
                        "Value": metrics["latency_ms"]["avg"],
                    },
                    {
                        "MetricName": "ThroughputRPS",
                        "Unit": "Count/Second",
                        "Value": metrics["throughput_rps"],
                    },
                    {
                        "MetricName": "RequestsPerMinute",
                        "Unit": "Count",
                        "Value": metrics["requests_per_minute"],
                    },
                    {
                        "MetricName": "CacheHitRate",
                        "Unit": "Percent",
                        "Value": metrics["cache_hit_rate"] * 100,
                    },
                    {
                        "MetricName": "CacheMissRate",
                        "Unit": "Percent",
                        "Value": metrics["cache_miss_rate"] * 100,
                    },
                ],
            )
            logger.info("Published CloudWatch metrics")
        except Exception as exc:  # pragma: no cover - network/AWS dependent
            logger.exception("Failed to publish metrics: %s", exc)

    def create_dashboard_definition(self) -> Dict[str, Any]:
        """Return a dashboard document for CloudWatch."""
        return {
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "title": "CodeIntel API - Latency",
                        "metrics": [
                            [self.namespace, "LatencyP50"],
                            [".", "LatencyP95"],
                            [".", "LatencyP99"],
                            [".", "LatencyAvg"],
                        ],
                        "view": "timeSeries",
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "stat": "Average",
                    },
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "title": "CodeIntel API - Reliability",
                        "metrics": [[self.namespace, "RequestCount"], [".", "ErrorRate"]],
                        "view": "timeSeries",
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "stat": "Average",
                    },
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "title": "CodeIntel API - Cache",
                        "metrics": [[self.namespace, "CacheHitRate"], [".", "CacheMissRate"]],
                        "view": "timeSeries",
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "stat": "Average",
                    },
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "title": "CodeIntel API - Throughput",
                        "metrics": [[self.namespace, "ThroughputRPS"], [".", "RequestsPerMinute"]],
                        "view": "timeSeries",
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "stat": "Average",
                    },
                },
            ]
        }

    def request_metrics_decorator(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorate a request handler to track latency/success/cache metrics."""

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception:
                latency_ms = (time.perf_counter() - started) * 1000
                self.record_request(latency_ms, success=False)
                raise

            latency_ms = (time.perf_counter() - started) * 1000
            cached: Optional[bool] = None
            if isinstance(result, dict):
                raw_latency = result.get("latency_ms")
                if isinstance(raw_latency, (int, float)):
                    latency_ms = float(raw_latency)
                raw_cached = result.get("cached")
                if isinstance(raw_cached, bool):
                    cached = raw_cached

            self.record_request(latency_ms, success=True, cached=cached)
            return result

        return wrapper

    def create_cloudwatch_dashboard(self, dashboard_name: str = "CodeIntel-API") -> Optional[Dict[str, Any]]:
        if self._cloudwatch is None:
            logger.debug("CloudWatch dashboard creation disabled")
            return None

        definition = self.create_dashboard_definition()
        try:
            return self._cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(definition),
            )
        except Exception as exc:  # pragma: no cover - network/AWS dependent
            logger.exception("Failed to create dashboard: %s", exc)
            return None
