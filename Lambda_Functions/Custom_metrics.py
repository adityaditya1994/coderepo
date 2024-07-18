import json
import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')

# DynamoDB tables
success_table = dynamodb.Table(os.environ['SUCCESS_TABLE'])
failure_table = dynamodb.Table(os.environ['FAILURE_TABLE'])

def lambda_handler(event, context):
    success_count = 0
    failure_count = 0

    for record in event['Records']:
        try:
            message = json.loads(record['body'])
            enriched_message = enrich_message(message)
            if meets_business_logic(enriched_message):
                success_table.put_item(Item=enriched_message)
                success_count += 1
            else:
                failure_table.put_item(Item=enriched_message)
                failure_count += 1
        except ClientError as e:
            print(f"Error: {e.response['Error']['Message']}")

    # Custom CloudWatch Metrics
    put_metric_data('SuccessCount', success_count)
    put_metric_data('FailureCount', failure_count)

    return {
        'statusCode': 200,
        'body': json.dumps('Processed {} records successfully, {} records failed'.format(success_count, failure_count))
    }

def meets_business_logic(message):
    # Business logic checks
    if not message.get('order_id'):
        return False
    if message.get('amount', 0) <= 0:
        return False
    if datetime.strptime(message['order_date'], '%Y-%m-%d') > datetime.now():
        return False
    return True

def enrich_message(message):
    # Enrich the message with additional fields
    message['processed_timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    if meets_business_logic(message):
        message['status'] = 'SUCCESS'
    else:
        message['status'] = 'FAILURE'
    return message

def put_metric_data(metric_name, value):
    response = cloudwatch.put_metric_data(
        MetricData=[
            {
                'MetricName': metric_name,
                'Unit': 'Count',
                'Value': value
            },
        ],
        Namespace='OrderProcessingMetrics'
    )
    print(f"Metric {metric_name} with value {value} sent to CloudWatch: {response}")
