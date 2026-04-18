from src.monitoring import MonitoringSystem


class StubCloudWatch:
    def __init__(self):
        self.calls = []

    def put_metric_data(self, **kwargs):
        self.calls.append(kwargs)


def test_metrics_include_cache_and_latency_aggregates():
    monitor = MonitoringSystem()
    monitor.record_request(100.0, success=True, cached=False)
    monitor.record_request(50.0, success=True, cached=True)
    monitor.record_request(200.0, success=False, cached=False)

    metrics = monitor.get_metrics()
    assert metrics["total_requests"] == 3
    assert metrics["cache_hits"] == 1
    assert metrics["cache_misses"] == 2
    assert metrics["cache_hit_rate"] == 1 / 3
    assert metrics["cache_miss_rate"] == 2 / 3
    assert metrics["latency_ms"]["avg"] > 0
    assert metrics["requests_per_minute"] > 0


def test_publish_cloudwatch_metrics_includes_extended_metrics():
    monitor = MonitoringSystem()
    cloudwatch = StubCloudWatch()
    monitor._cloudwatch = cloudwatch
    monitor.record_request(100.0, success=True, cached=False)
    monitor.record_request(50.0, success=True, cached=True)

    monitor.publish_cloudwatch_metrics()

    assert len(cloudwatch.calls) == 1
    metric_names = {m["MetricName"] for m in cloudwatch.calls[0]["MetricData"]}
    assert "LatencyP50" in metric_names
    assert "LatencyP95" in metric_names
    assert "LatencyP99" in metric_names
    assert "LatencyAvg" in metric_names
    assert "ErrorRate" in metric_names
    assert "RequestsPerMinute" in metric_names
    assert "CacheHitRate" in metric_names
    assert "CacheMissRate" in metric_names


def test_request_metrics_decorator_tracks_success_and_failure():
    monitor = MonitoringSystem()

    @monitor.request_metrics_decorator
    def successful_call():
        return {"completion": "ok", "latency_ms": 12.0, "cached": True}

    @monitor.request_metrics_decorator
    def failing_call():
        raise ValueError("boom")

    successful_call()
    try:
        failing_call()
    except ValueError:
        pass

    metrics = monitor.get_metrics()
    assert metrics["success_requests"] == 1
    assert metrics["error_requests"] == 1
    assert metrics["cache_hits"] == 1
