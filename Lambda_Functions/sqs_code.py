import json
import boto3


queue_url = r'https://sqs.eu-north-1.amazonaws.com/891377344475/ahs-sqs-demo-1907'

def send_sqs_message(queue_url):
    sqs = boto3.client('sqs')
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=('Id2: This is a sample message we are sending pn 20July'
        )
    )
    print(response['MessageId'])
    return 'Success'

def receive_sqs_message(queue_url):
    sqs = boto3.client('sqs')
    response = sqs.receive_message(
    QueueUrl=queue_url,
    MaxNumberOfMessages=1,
    MessageAttributeNames=[
        'All'
    ],
    VisibilityTimeout=10
    )
    print(response)
    print('This was response')
    message = response['Messages'][0]
    print(message)
    print('This was message')
    receipt_handle = message['ReceiptHandle']
    print(receipt_handle)
    print('This was receipt_handle')
    return receipt_handle
    
def delete_sqs_message(queue_url, receipt_handle):
    sqs = boto3.client('sqs')
    print('About to delete the message')
    response = sqs.delete_message(
    QueueUrl=queue_url,
    ReceiptHandle=receipt_handle
    )
    print('Message was deleted')
    return response




def lambda_handler(event, context):
    
    send_sqs_message(queue_url)
    receipt_handle = receive_sqs_message(queue_url)
    out = delete_sqs_message(queue_url, receipt_handle)
    print(out)
    print('This was the output value')
    

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
