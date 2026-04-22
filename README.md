# CodeIntel-AI-Ecosystem

Production-ready GPT-2 code completion REST API with in-memory caching, rate limiting, load testing, and optional CloudWatch monitoring (metrics + dashboard).

## Architecture (text diagram)

```text
Client Apps (IDEs / scripts)
   |
   v
Flask API (src/api.py)
   |-- POST /api/complete  (X-API-Key + rate limit)
   |-- GET  /api/health
   |-- GET  /api/metrics   (X-API-Key)
   |
   v
Model Manager (src/model.py)
   |-- GPT-2 lazy loading (CPU / CUDA)
   |-- in-memory LRU cache
   |-- single + batch completion
   |
   v
Monitoring (src/monitoring.py)
   |-- p50/p95/p99 + min/max/avg latency
   |-- throughput (RPS) + requests/min
   |-- error rate + cost estimation
   |-- optional CloudWatch publish + dashboard creation
```

## Quick start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment:

```bash
export API_KEY="test-key"
export MODEL_NAME="gpt2"

# Optional CloudWatch publishing
export ENABLE_CLOUDWATCH="false"   # set to "true" to publish to CloudWatch
export CLOUDWATCH_NAMESPACE="CodeIntelAPI"
export AWS_REGION="us-east-1"

# Optional cost model
export COST_PER_1000_REQUESTS_USD="0.25"
```

3. Run API:

```bash
python src/api.py
```

Server starts on `http://localhost:5000`.

## API

### `POST /api/complete`
Generate code completion using GPT-2.

Headers:
- `X-API-Key: <your key>`
- `Content-Type: application/json`

Body:

```json
{
  "code": "def add(a, b):",
  "max_new_tokens": 64
}
```

Success response (`200`):

```json
{
  "completion": "return a + b",
  "latency_ms": 134.2,
  "cached": false,
  "model": "gpt2"
}
```

Error codes:
- `400` invalid input
- `401` missing/invalid API key
- `429` rate limit exceeded (100 requests/minute)
- `500` internal error

### `GET /api/health`
Returns service health:

```json
{
  "status": "ok",
  "model": "gpt2"
}
```

### `GET /api/metrics`
Returns API + model metrics (requires `X-API-Key`).

## Load testing

```bash
python load_testing/load_test.py --url http://localhost:5000/api/complete --workers 50 --duration 60 --api-key test-key
```

Workers supported: `10`, `50`, `100`.

Outputs:
- min/max/p50/p95/p99 latency
- throughput (requests/sec)
- error rate
- JSON report at `load_testing/results/load_test_results.json`

## CloudWatch (optional)

Enable CloudWatch publishing:

```bash
export ENABLE_CLOUDWATCH="true"
```

The service publishes these custom metrics to the namespace (default `CodeIntelAPI`):
- `RequestCount`, `ErrorRate`
- `LatencyP50`, `LatencyP95`, `LatencyP99`, `LatencyAvg`
- `ThroughputRPS`, `RequestsPerMinute`
- `CacheHitRate`, `CacheMissRate`

A CloudWatch dashboard definition is available via `MonitoringSystem.create_dashboard_definition()`.

## Deployment notes

This repository includes a sample SageMaker endpoint configuration at `deployment/sagemaker_config.json` (instance type, autoscaling, and alarm thresholds).

## Scalability recommendations

1. Track p95 latency + error rate in CloudWatch (when enabled).
2. Scale out inference (and consider GPU) if latency rises under load.
3. Use a shared cache (e.g., Redis) if repeated prompts dominate traffic.
4. Run load-test profiles (10/50/100 workers) before releases.