# CodeIntel-AI-Ecosystem

Production-ready GPT-2 code completion API with monitoring, load testing, and AWS SageMaker deployment configuration.

## Architecture (text diagram)

```text
Client Apps
   |
   v
Flask API (src/api.py)
   |-- /api/health
   |-- /api/complete  (API key + rate limit)
   |-- /api/metrics
   |
   v
Model Manager (src/model.py)
   |-- GPT-2 lazy loading + in-memory cache
   |-- single + batch completion
   |-- latency counters
   |
   v
Monitoring (src/monitoring.py)
   |-- p50/p95/p99 latency
   |-- throughput + error rate
   |-- estimated cost per 1000 requests
   |-- optional CloudWatch metrics/dashboard
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
# Optional
export ENABLE_CLOUDWATCH="false"
export COST_PER_1000_REQUESTS_USD="0.25"
```

3. Run API:

```bash
python src/api.py
```

Server starts on `http://localhost:5000`.

## API documentation

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

## Deployment instructions (Docker + SageMaker)

### Build Docker image

```bash
docker build -t codeintel-api .
```

### Run container

```bash
docker run -p 8080:8080 -e API_KEY=test-key codeintel-api
```

### SageMaker configuration
Use `deployment/sagemaker_config.json` for endpoint sizing and autoscaling:
- Instance type: `ml.m5.large`
- Auto scaling: min `1`, max `4`
- CloudWatch alarm thresholds included
- Cost optimization defaults included

## Load testing guide

Run load tests against the API:

```bash
python load_testing/load_test.py --workers 50 --duration 60 --api-key test-key
```

Supported worker configurations: `10`, `50`, `100`.

Outputs include:
- min/max/p50/p95/p99 latency
- throughput (requests/sec)
- error rate
- JSON report at `load_testing/results/load_test_results.json`

## Cost analysis framework

The monitoring system estimates:

```text
estimated_cost_usd = (total_requests / 1000) * estimated_cost_per_1000_requests_usd
```

Tune with environment variable:
- `COST_PER_1000_REQUESTS_USD`

## Scalability recommendations

1. Keep autoscaling min=1 and max=4 for cost/performance balance.
2. Track p95 latency and error rate alarms in CloudWatch.
3. Add managed caching (Redis) for repeated prompts if traffic grows.
4. Use load-test profiles (10/50/100 workers) before each release.
