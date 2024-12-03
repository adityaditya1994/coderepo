import json
import boto3
import time
import os

# Initialize S3 client
s3_client = boto3.client('s3')

# Define S3 bucket name
s3_bucket = os.environ['s3_bucket']
s3_key_prefix = 'transformed-data/'

# Transformation logic for 'status'
def transform_status(status):
    # Industry logic: Map statuses to actionable categories
    status_map = {
        'active': 'Operational',
        'inactive': 'Standby',
        'faulty': 'Requires Maintenance'
    }
    return status_map.get(status, 'Unknown')

# Transformation logic for 'event_type'
def transform_event_type(event_type):
    # Industry logic: Map events to standardized codes
    event_type_map = {
        'sensor_reading': 'E101',
        'alert': 'E202',
        'heartbeat': 'E303'
    }
    return event_type_map.get(event_type, 'E000')

# Transformation logic for 'location'
def transform_location(location):
    # Industry logic: Add region and geohash based on coordinates
    latitude = location['latitude']
    longitude = location['longitude']
    
    # Determine the region based on latitude and longitude
    if latitude > 0:
        region = 'Northern Hemisphere'
    else:
        region = 'Southern Hemisphere'
        
    if longitude > 0:
        region += ', Eastern'
    else:
        region += ', Western'
    
    # Create a geohash-like string
    geohash = f"{round(latitude, 2)}|{round(longitude, 2)}"
    
    # Add the new fields
    location['region'] = region
    location['geohash'] = geohash
    
    return location

# Main record transformation function
def transform_record(record):
    data = json.loads(record['kinesis']['data'])
    
    # Transform 'status'
    data['status_transformed'] = transform_status(data['status'])
    
    # Transform 'event_type'
    data['event_type_transformed'] = transform_event_type(data['event_type'])
    
    # Transform 'location'
    data['location_transformed'] = transform_location(data['location'])
    
    # Add an additional field: 'priority_level' based on status and event type
    if data['status_transformed'] == 'Requires Maintenance' or data['event_type_transformed'] == 'E202':
        data['priority_level'] = 'High'
    else:
        data['priority_level'] = 'Normal'
    
    return data

# Lambda handler function
def lambda_handler(event, context):
    transformed_data = []
    
    # Process each record in the Kinesis event
    for record in event['Records']:
        transformed_data.append(transform_record(record))
    
    # Write transformed data to S3
    file_name = f"{s3_key_prefix}transformed_{int(time.time())}.json"
    s3_client.put_object(
        Bucket=s3_bucket,
        Key=file_name,
        Body=json.dumps(transformed_data)
    )
    
    print(f"Transformed data written to S3: {file_name}")

    return {
        'statusCode': 200,
        'body': json.dumps('Data transformed and written to S3 successfully!')
    }
