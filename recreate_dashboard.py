import boto3
import json
import os

os.environ['AWS_REGION'] = 'us-east-1'

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

# Separated dashboard definition
dashboard_body = {
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    ["CodeIntel-API", "LatencyAvg"],
                    [".", "LatencyP50"],
                    [".", "LatencyP95"],
                    [".", "LatencyP99"]
                ],
                "period": 60,
                "stat": "Average",
                "region": "us-east-1",
                "title": "Latency (ms)",
                "yAxis": {"left": {"min": 0}}
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    ["CodeIntel-API", "RequestCount"],
                    [".", "ErrorRate"]
                ],
                "period": 60,
                "stat": "Sum",
                "region": "us-east-1",
                "title": "Requests & Error Rate"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    ["CodeIntel-API", "CacheHitRate"],
                    [".", "CacheMissRate"]
                ],
                "period": 60,
                "stat": "Average",
                "region": "us-east-1",
                "title": "Cache Hit/Miss Rate (%)"
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    ["CodeIntel-API", "ThroughputRPS"],
                    [".", "RequestsPerMinute"]
                ],
                "period": 60,
                "stat": "Average",
                "region": "us-east-1",
                "title": "Throughput"
            }
        }
    ]
}

response = cloudwatch.put_dashboard(
    DashboardName='CodeIntel-API',
    DashboardBody=json.dumps(dashboard_body)
)
print("Dashboard updated with 4 separate widgets!")
print(response)
