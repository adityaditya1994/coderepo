import json
import boto3
import random
import time
import os
# Initialize Kinesis client
kinesis_client = boto3.client('kinesis')

# Define the name of the Kinesis stream
stream_name = os.environ['kinesis_name']

# Function to generate sample data
def generate_sample_data(num_records):
    records = []
    for _ in range(num_records):
        data = {
            'sensor_id': random.randint(1, 100),
            'temperature': random.uniform(20.0, 40.0),
            'humidity': random.uniform(40.0, 80.0),
            'timestamp': int(time.time())
        }
        records.append({'Data': json.dumps(data), 'PartitionKey': 'partition_key'})
    return records

# Lambda handler function
def lambda_handler(event, context):
    # Generate sample data
    num_records = 100  # Adjust the number of records as needed
    records = generate_sample_data(num_records)
    
    # Put records into the Kinesis stream
    response = kinesis_client.put_records(
        Records=records,
        StreamName=stream_name
    )
    
    print("Records sent to Kinesis stream:", response)

    return {
        'statusCode': 200,
        'body': json.dumps('Data sent to Kinesis stream successfully!')
    }
