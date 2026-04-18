import boto3
import os

# Set credentials
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')

try:
    client = boto3.client('cloudwatch', region_name='us-east-1')
    response = client.list_metrics(Namespace='CodeIntelAPI')
    print("SUCCESS! CloudWatch is accessible")
    print(f"Found {len(response['Metrics'])} metrics")
    for metric in response['Metrics']:
        print(f"  - {metric['MetricName']}")
except Exception as e:
    print(f"ERROR: {e}")
