import boto3

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
sns_arn = 'arn:aws:sns:us-east-1:933793947363:codeintel-monitoring-alerts'

cloudwatch.put_metric_alarm(
    AlarmName='CodeIntel-Low-Request-Rate',
    ComparisonOperator='LessThanThreshold',
    EvaluationPeriods=1,
    MetricName='RequestsPerMinute',
    Namespace='CodeIntel-API',  # CORRECT namespace with dash
    Period=60,
    Statistic='Average',
    Threshold=1.0,
    ActionsEnabled=True,
    AlarmActions=[sns_arn],
    OKActions=[sns_arn],
    AlarmDescription='Alarm when requests per minute drop below threshold or no data is reported',
    TreatMissingData='breaching'
)

print("✅ Fixed CodeIntel-Low-Request-Rate namespace to CodeIntel-API")

alarms_config = [
    {
        'name': 'CodeIntel-High-Cache-Miss-Rate',
        'metric': 'CacheMissRate',
        'comparison': 'GreaterThanThreshold',
        'threshold': 50,
        'stat': 'Average'
    },
    {
        'name': 'CodeIntel-High-Latency',
        'metric': 'LatencyAvg',
        'comparison': 'GreaterThanThreshold',
        'threshold': 500,
        'stat': 'Average'
    },
    {
        'name': 'CodeIntel-High-Error-Rate',
        'metric': 'ErrorRate',
        'comparison': 'GreaterThanThreshold',
        'threshold': 5,
        'stat': 'Average'
    }
]

for alarm in alarms_config:
    cloudwatch.put_metric_alarm(
        AlarmName=alarm['name'],
        ComparisonOperator=alarm['comparison'],
        EvaluationPeriods=1,
        MetricName=alarm['metric'],
        Namespace='CodeIntel-API',  # CORRECT namespace
        Period=60,
        Statistic=alarm['stat'],
        Threshold=alarm['threshold'],
        ActionsEnabled=True,
        AlarmActions=[sns_arn],
        OKActions=[sns_arn],
        TreatMissingData='notBreaching'
    )
    print(f"✅ Fixed {alarm['name']}")

print("\n✅ All alarms updated to CodeIntel-API namespace!")
