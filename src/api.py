"""Production Flask API for GPT-2 code completion."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable, Deque, Dict, Tuple

from flask import Flask, Response, jsonify, request

from src.model import ModelManager
from src.monitoring import MonitoringSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _make_cors_response(resp: Response) -> Response:
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,X-API-Key"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return resp


class InMemoryRateLimiter:
    """Simple fixed-window rate limiter per client identity."""

    def __init__(self, limit: int = 100, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, identity: str) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - self.window_seconds
        queue = self._requests[identity]
        while queue and queue[0] < window_start:
            queue.popleft()

        if len(queue) >= self.limit:
            retry_after = int(queue[0] + self.window_seconds - now) + 1
            return False, max(retry_after, 1)

        queue.append(now)
        return True, 0


def create_app(
    model_manager: ModelManager | None = None,
    monitor: MonitoringSystem | None = None,
) -> Flask:
    app = Flask(__name__)
    api_key = os.getenv("API_KEY", "test-key")

    model_manager = model_manager or ModelManager(model_name=os.getenv("MODEL_NAME", "gpt2"))
    monitor = monitor or MonitoringSystem(namespace=os.getenv("CLOUDWATCH_NAMESPACE", "CodeIntelAPI"))
    limiter = InMemoryRateLimiter(limit=100, window_seconds=60)

    @app.before_request
    def log_request() -> None:
        if request.method == "OPTIONS":
            return
        logger.info("request method=%s path=%s ip=%s", request.method, request.path, request.remote_addr)

    @app.after_request
    def add_headers(resp: Response) -> Response:
        if request.method != "OPTIONS":
            logger.info("response status=%s path=%s", resp.status_code, request.path)
        return _make_cors_response(resp)

    def require_api_key(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if request.method == "OPTIONS":
                return fn(*args, **kwargs)
            provided = request.headers.get("X-API-Key")
            if provided != api_key:
                return jsonify({"error": "Unauthorized"}), 401
            return fn(*args, **kwargs)

        return wrapper

    def require_rate_limit() -> Tuple[bool, Response | None]:
        identity = f"{request.remote_addr}:{request.headers.get('X-API-Key', '')}"
        allowed, retry_after = limiter.allow(identity)
        if not allowed:
            response = jsonify({"error": "Rate limit exceeded"})
            response.status_code = 429
            response.headers["Retry-After"] = str(retry_after)
            return False, response
        return True, None

    @app.route("/api/complete", methods=["POST", "OPTIONS"])
    @require_api_key
    def complete() -> Response:
        if request.method == "OPTIONS":
            return _make_cors_response(Response(status=204))

        allowed, rate_response = require_rate_limit()
        if not allowed and rate_response is not None:
            return rate_response

        started = time.perf_counter()
        try:
            payload = request.get_json(silent=True) or {}
            code = payload.get("code", "")
            max_new_tokens = int(payload.get("max_new_tokens", 64))
            request_wrapper = getattr(monitor, "request_metrics_decorator", None)
            if callable(request_wrapper):
                result = request_wrapper(model_manager.complete)(code=code, max_new_tokens=max_new_tokens)
            else:
                result = model_manager.complete(code=code, max_new_tokens=max_new_tokens)
                monitor.record_request(result["latency_ms"], success=True)
            monitor.publish_cloudwatch_metrics()
            return jsonify(result), 200
        except ValueError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            monitor.record_request(latency_ms, success=False)
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:  # pragma: no cover - runtime guard
            latency_ms = (time.perf_counter() - started) * 1000
            monitor.record_request(latency_ms, success=False)
            logger.exception("Unhandled completion error: %s", exc)
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/api/health", methods=["GET", "OPTIONS"])
    def health() -> Response:
        if request.method == "OPTIONS":
            return _make_cors_response(Response(status=204))

        return jsonify({"status": "ok", "model": model_manager.model_name}), 200

    @app.route("/api/metrics", methods=["GET", "OPTIONS"])
    @require_api_key
    def metrics() -> Response:
        if request.method == "OPTIONS":
            return _make_cors_response(Response(status=204))

        return (
            jsonify(
                {
                    "api": monitor.get_metrics(),
                    "model": model_manager.get_metrics(),
                }
            ),
            200,
        )

    @app.errorhandler(404)
    def not_found(_: Exception) -> Response:
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_: Exception) -> Response:
        return jsonify({"error": "Method not allowed"}), 405

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
