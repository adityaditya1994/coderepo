####### Put data into Landing

import boto3
import json
import random
import string
import os

s3_client = boto3.client('s3')

def generate_customer_data(num_records=10000):
    data = []
    for _ in range(num_records):
        customer = {
            "customer_id": ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
            "name": ''.join(random.choices(string.ascii_lowercase, k=5)),
            "age": random.randint(18, 70),
            "subscription_type": random.choice(["Basic", "Standard", "Premium"]),
            "signup_date": f"2024-09-{random.randint(1, 30)}",
            "active": random.choice([True, False])
        }
        data.append(customer)
    return data

def lambda_handler(event, context):
    # Generate synthetic data
    data = generate_customer_data()

    # Define bucket and path
    bucket_name = os.environ['bucket_name']
    landing_layer_key = 'landing_rat/netflix_customers.json'

    # Upload data to S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key=landing_layer_key,
        Body=json.dumps(data)
    )

    # Trigger the next Lambda function
    return {
        'statusCode': 200,
        'message': 'Data ingested into the landing layer successfully!',
        'bucket_name': bucket_name,
        'landing_layer_key': landing_layer_key
    }
