"""
{
  "id": "456",
  "name": "Alice Wonderland",
  "age": 22
}
"""
## sample message

import json
import boto3
import os

sqs = boto3.client('sqs')
dynamodb = boto3.client('dynamodb')


 def get_queue_url():
    queue_name = os.environ['queue_name']
    aws_region = os.environ['region']
    sqs = boto3.client('sqs', region_name=aws_region)
    try:
        # Get the URL of the SQS queue
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']

        print(f"The URL of the SQS queue '{queue_name}' is: {queue_url}")
        return queue_url

        # Now you can use 'queue_url' as needed in your Lambda function
    except Exception as e:
        print(f"Error getting SQS queue URL: {e}")


def process_message(message_body):
    # ETL logic: Normalize the 'name' field to uppercase
    message_body['name'] = message_body['name'].upper()

    # ETL logic: Add a new field 'isAdult' based on the 'age'
    message_body['isAdult'] = message_body['age'] >= 18

    return message_body

def put_item_into_dynamodb(data):
    try:
        # Assuming 'TableName' is the name of your DynamoDB table
        table_name = os.environ['table_name']

        # Put the processed data into DynamoDB
        dynamodb.put_item(
            TableName=table_name,
            Item={
                'id': {'S': data['id']},
                'name': {'S': data['name']},
                'age': {'N': str(data['age'])},
                'isAdult': {'BOOL': data['isAdult']},
                # Add more attributes as needed
            }
        )

        print(f"Successfully loaded data into DynamoDB: {data}")
        return True
    except Exception as e:
        print(f"Error loading data into DynamoDB: {e}")
        return False

def delete_message(receipt_handle):
    # Assuming 'YourQueueURL' is the URL of your SQS queue
    queue_url = get_queue_url

    # Delete the message from the SQS queue
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )

    print(f"Successfully deleted message from SQS queue")

def lambda_handler(event, context):
    # Retrieve the SQS event record
    for record in event['Records']:
        # Get the message body from the SQS record
        message_body = json.loads(record['body'])

        # Extract data or perform any processing as needed
        processed_data = process_message(message_body)

        # Load processed data into DynamoDB
        success = put_item_into_dynamodb(processed_data)

        # Delete the processed message from the SQS queue if loaded successfully
        if success:
            delete_message(record['receiptHandle'])
    return {
    'statusCode': 200,
    'body': json.dumps('Hello from Lambda!')
        }




