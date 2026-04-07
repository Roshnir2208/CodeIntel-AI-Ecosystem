"""
Batch processing for multiple code samples
"""

import json
import boto3
import logging
from datetime import datetime
from typing import List, Dict

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def process_batch(samples: List[Dict]) -> Dict:
    """Process batch of code samples"""
    
    results = []
    errors = []
    
    for sample in samples:
        try:
            # Placeholder for batch processing logic
            result = {
                "sample_id": sample.get("id"),
                "status": "processed",
                "timestamp": datetime.utcnow().isoformat()
            }
            results.append(result)
        except Exception as e:
            errors.append({
                "sample_id": sample.get("id"),
                "error": str(e)
            })
    
    # Notify if there are errors
    if errors:
        send_alert(f"Batch processing completed with {len(errors)} errors", errors)
    
    return {
        "total_processed": len(results),
        "total_errors": len(errors),
        "results": results,
        "errors": errors
    }


def send_alert(subject: str, message: dict):
    """Send SNS alert"""
    try:
        sns.publish(
            TopicArn='arn:aws:sns:us-east-1:ACCOUNT_ID:codeintel-alerts',
            Subject=subject,
            Message=json.dumps(message, indent=2)
        )
    except Exception as e:
        logger.warning(f"Failed to send alert: {str(e)}")