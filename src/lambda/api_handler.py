"""
Lambda function for handling API requests
Integrates with SageMaker endpoint for inference
"""

import json
import boto3
import time
import logging
from datetime import datetime

sagemaker_runtime = boto3.client('sagemaker-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

table = dynamodb.Table('CodeIntel-Predictions')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

SAGEMAKER_ENDPOINT = 'codeintel-endpoint'


def lambda_handler(event, context):
    """
    Main API handler
    Event payload:
    {
        "code": "python code snippet",
        "task": "summarize|document|bugs|optimize",
        "language": "python|javascript|java"
    }
    """
    
    start_time = time.time()
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        code_snippet = body.get('code', '')
        task_type = body.get('task', 'summarize')
        language = body.get('language', 'python')
        
        if not code_snippet:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Code snippet required'})
            }
        
        # Prepare payload for SageMaker
        payload = {
            'code': code_snippet,
            'task': task_type,
            'language': language
        }
        
        # Invoke SageMaker endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        # Parse response
        result = json.loads(response['Body'].read())
        execution_time = (time.time() - start_time) * 1000  # ms
        result['execution_time_ms'] = execution_time
        
        # Log to DynamoDB
        log_prediction(
            code_snippet=code_snippet[:100],
            task=task_type,
            language=language,
            result=result,
            latency_ms=execution_time
        )
        
        # Send CloudWatch metrics
        send_metrics(execution_time, task_type)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def log_prediction(code_snippet: str, task: str, language: str, result: dict, latency_ms: float):
    """Log prediction to DynamoDB"""
    try:
        table.put_item(
            Item={
                'prediction_id': f"{int(time.time() * 1000)}",
                'timestamp': datetime.utcnow().isoformat(),
                'task': task,
                'language': language,
                'code_snippet': code_snippet,
                'result': json.dumps(result),
                'latency_ms': latency_ms,
                'ttl': int(time.time()) + 86400 * 30
            }
        )
    except Exception as e:
        logger.warning(f"Failed to log prediction: {str(e)}")


def send_metrics(latency_ms: float, task_type: str):
    """Send metrics to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace='CodeIntel',
            MetricData=[
                {
                    'MetricName': 'AnalysisLatency',
                    'Value': latency_ms,
                    'Unit': 'Milliseconds',
                    'Dimensions': [
                        {'Name': 'TaskType', 'Value': task_type}
                    ]
                }
            ]
        )
    except Exception as e:
        logger.warning(f"Failed to send metrics: {str(e)}")