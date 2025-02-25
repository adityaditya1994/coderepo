####### grouping the data and aggregation

import boto3
import json

s3_client = boto3.client('s3')

def aggregate_data(customers):
    # Example aggregation: Count customers per subscription type
    metrics = {}
    for customer in customers:
        subscription_type = customer['subscription_type']
        if subscription_type not in metrics:
            metrics[subscription_type] = 0
        metrics[subscription_type] += 1
    return metrics

def lambda_handler(event, context):
    # Get bucket and key information from the event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']

    # Read pass data from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    pass_data = json.loads(response['Body'].read())

    # Perform aggregation
    metrics = aggregate_data(pass_data)

    # Define key for metrics file in the business layer
    metrics_key = 'business/metrics/customers_metrics.json'

    # Write metrics data back to S3
    s3_client.put_object(Bucket=bucket_name, Key=metrics_key, Body=json.dumps(metrics))

    return {
        'statusCode': 200,
        'message': 'Data aggregated and metrics stored in the business layer successfully!',
        'bucket_name': bucket_name,
        'metrics_key': metrics_key
    }
