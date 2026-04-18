# CloudWatch Monitoring & Alerts

This project includes production-oriented CloudWatch monitoring for the API.

## What is monitored

`src/monitoring.py` publishes the following custom metrics to namespace `CodeIntelAPI` (configurable):

- `LatencyP50`, `LatencyP95`, `LatencyP99`, `LatencyAvg` (ms)
- `RequestCount`
- `ErrorRate` (%)
- `ThroughputRPS`
- `RequestsPerMinute`
- `CacheHitRate` (%)
- `CacheMissRate` (%)

The monitoring dashboard visualizes:

- Real-time latency (p50/p95/p99 + avg)
- Request count and error rate
- Cache hit/miss rate
- Throughput (RPS and requests/minute)

## Alarms

The CloudFormation stack provisions alarms for:

1. **HighAverageLatencyAlarm**: `LatencyAvg > 500 ms`
2. **HighErrorRateAlarm**: `ErrorRate > 5%`
3. **LowRequestRateAlarm**: `RequestsPerMinute < threshold` (missing data treated as breaching)
4. **HighCacheMissRateAlarm**: `CacheMissRate > 50%`

All alarms notify a shared SNS topic.

## Deploy (one command)

From repository root:

```bash
./scripts/deploy-monitoring.sh codeintel-monitoring your-email@example.com
```

Optional environment overrides:

```bash
export NAMESPACE=CodeIntelAPI
export ALARM_PERIOD_SECONDS=60
export LOW_REQUEST_THRESHOLD_PER_MINUTE=1
./scripts/deploy-monitoring.sh codeintel-monitoring your-email@example.com
```

CloudFormation template path:

`infrastructure/cloudwatch-monitoring.yaml`

## SNS notifications

- Email is required via `AlertEmail` parameter.
- Confirm the SNS subscription from your inbox after deployment.
- Alarm notifications from CloudWatch/SNS include timestamp, current metric value, and threshold details.
- Slack integration is optional and can be added using AWS Chatbot subscribed to the same SNS topic.

## API integration notes

- `MonitoringSystem.record_request(...)` now accepts optional `cached` and `request_count` fields while remaining backward compatible with existing calls.
- `MonitoringSystem.request_metrics_decorator` can wrap request/model handlers to automatically track:
  - success/failure
  - latency
  - cache hit/miss when `cached` is present in result payload

## Verifying metric publication with load test

1. Enable CloudWatch publishing:

```bash
export ENABLE_CLOUDWATCH=true
export AWS_REGION=us-east-1
export CLOUDWATCH_NAMESPACE=CodeIntelAPI
```

2. Run the API and send traffic:

```bash
python load_testing/load_test.py --workers 10 --duration 60 --api-key test-key
```

3. In AWS Console:
   - Open CloudWatch → Dashboards → `CodeIntel-API`
   - Confirm metrics update
   - Validate alarm state transitions by generating synthetic high-latency/error traffic if needed
