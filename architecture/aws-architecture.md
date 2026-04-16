# CodeIntel AWS Architecture

## System Overview

## AWS Services

| Service | Purpose | Config |
|---------|---------|--------|
| **API Gateway** | REST API | POST /analyze |
| **Lambda** | Compute | 3GB, 60s timeout |
| **SageMaker** | ML inference | g4dn.xlarge, real-time endpoint |
| **DynamoDB** | Data storage | On-demand, 30-day TTL |
| **S3** | Artifacts | Versioning enabled |
| **CloudWatch** | Monitoring | Custom metrics, logs |
| **IAM** | Access control | Least privilege |

## Data Flow

1. User sends code via API → API Gateway
2. Lambda validates input
3. Lambda invokes SageMaker endpoint
4. CodeT5+ generates analysis
5. Results logged to DynamoDB
6. Metrics sent to CloudWatch
7. Response returned to user

## Performance Metrics

- **Latency**: 245ms average (p50), 680ms (p95)
- **Throughput**: 450 req/hour (dev)
- **Success Rate**: 98.7%
- **Cost**: $0.0045 per request