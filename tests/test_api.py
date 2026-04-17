import os

from src.api import create_app


class StubModelManager:
    model_name = "stub"

    def __init__(self):
        self.calls = 0

    def complete(self, code: str, max_new_tokens: int = 64):
        self.calls += 1
        if not code:
            raise ValueError("'code' must be a non-empty string")
        return {
            "completion": "return a + b",
            "latency_ms": 1.5,
            "cached": False,
            "model": "stub",
        }

    def get_metrics(self):
        return {"request_count": 1.0, "average_latency_ms": 1.5, "cache_entries": 0.0}


class StubMonitor:
    def __init__(self):
        self.records = []

    def record_request(self, latency_ms: float, success: bool):
        self.records.append((latency_ms, success))

    def publish_cloudwatch_metrics(self):
        return None

    def get_metrics(self):
        return {
            "total_requests": len(self.records),
            "success_requests": sum(1 for _, s in self.records if s),
            "error_requests": sum(1 for _, s in self.records if not s),
            "error_rate": 0.0,
            "throughput_rps": 1.0,
            "latency_ms": {"p50": 1.0, "p95": 1.0, "p99": 1.0, "min": 1.0, "max": 1.0},
            "estimated_cost_usd": 0.0,
            "estimated_cost_per_1000_requests_usd": 0.25,
        }


def build_client():
    os.environ["API_KEY"] = "test-key"
    app = create_app(model_manager=StubModelManager(), monitor=StubMonitor())
    app.config["TESTING"] = True
    return app.test_client()


def test_health_endpoint():
    client = build_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_complete_requires_api_key():
    client = build_client()
    response = client.post("/api/complete", json={"code": "def add(a,b):"})
    assert response.status_code == 401


def test_complete_success_and_metrics():
    client = build_client()
    response = client.post(
        "/api/complete",
        json={"code": "def add(a,b):"},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 200
    assert "completion" in response.get_json()

    metrics = client.get("/api/metrics", headers={"X-API-Key": "test-key"})
    assert metrics.status_code == 200
    body = metrics.get_json()
    assert "api" in body
    assert "model" in body


def test_rate_limit_enforced():
    client = build_client()
    headers = {"X-API-Key": "test-key"}
    for _ in range(100):
        response = client.post("/api/complete", json={"code": "x=1"}, headers=headers)
        assert response.status_code == 200

    limited = client.post("/api/complete", json={"code": "x=1"}, headers=headers)
    assert limited.status_code == 429
