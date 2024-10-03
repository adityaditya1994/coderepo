####### Validate data and moe to processing layer

import boto3
import json

s3_client = boto3.client('s3')

def validate_customer_data(customers):
    pass_data = []
    fail_data = []

    for customer in customers:
        # Define some basic validation rules
        if customer['age'] < 18 or customer['age'] > 100:
            fail_data.append(customer)
        elif customer['subscription_type'] not in ["Basic", "Standard", "Premium"]:
            fail_data.append(customer)
        else:
            pass_data.append(customer)

    return pass_data, fail_data

def lambda_handler(event, context):
    # Get bucket and key information from the event
    bucket_name = event['bucket_name']
    landing_layer_key = event['landing_layer_key']

    # Read data from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=landing_layer_key)
    customer_data = json.loads(response['Body'].read())

    # Validate data
    pass_data, fail_data = validate_customer_data(customer_data)

    # Define keys for pass and fail files in the processing layer
    pass_key = 'processing/pass/customers_pass.json'
    fail_key = 'processing/fail/customers_fail.json'

    # Write pass and fail data back to S3
    s3_client.put_object(Bucket=bucket_name, Key=pass_key, Body=json.dumps(pass_data))
    s3_client.put_object(Bucket=bucket_name, Key=fail_key, Body=json.dumps(fail_data))

    # Trigger the next Lambda function
    return {
        'statusCode': 200,
        'message': 'Data validated and moved to the processing layer successfully!',
        'bucket_name': bucket_name,
        'pass_key': pass_key,
        'fail_key': fail_key
    }
