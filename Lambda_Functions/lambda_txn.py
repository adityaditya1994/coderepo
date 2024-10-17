import json
import boto3

# Initialize the DynamoDB resource
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ahs-txn-table-1710')

# # Initialize CloudWatch client for custom metrics
# cloudwatch = boto3.client('cloudwatch')


# {
#     'sender_id': '2',
#     'receiver_id': '1',
#     'amount': 30
# }

def lambda_handler(event, context):
    print(event)
    for messages in event['Records']:
        message = messages['body']
        sender_id = message['sender_id']
        receiver_id = message['receiver_id']
        amount = message['amount']

        # Business Logic: Transfer amount from sender to receiver
        try:
            # Begin the transaction
            with table.batch_writer() as batch:
                # Debit the sender's account
                sender_account = table.get_item(Key={'account_id': sender_id})['Item']
                if sender_account['balance'] < amount:
                    raise ValueError("Insufficient balance")

                new_sender_balance = sender_account['balance'] - amount
                table.update_item(
                    Key={'account_id': sender_id},
                    UpdateExpression="set balance = :new_balance",
                    ExpressionAttributeValues={':new_balance': new_sender_balance}
                )

                # Credit the receiver's account
                receiver_account = table.get_item(Key={'account_id': receiver_id})['Item']
                new_receiver_balance = receiver_account['balance'] + amount
                table.update_item(
                    Key={'account_id': receiver_id},
                    UpdateExpression="set balance = :new_balance",
                    ExpressionAttributeValues={':new_balance': new_receiver_balance}
                )

                # Put CloudWatch metrics for successful transactions
                # cloudwatch.put_metric_data(
                #     MetricData=[
                #         {
                #             'MetricName': 'SuccessfulTransactions',
                #             'Unit': 'Count',
                #             'Value': 1
                #         },
                #     ],
                #     Namespace='BankingApp/Transactions'
                # )

        except Exception as e:
            # Log failure to a different DynamoDB table for failed transactions (or log it)
            print(f"Transaction failed: {str(e)}")

            # Put CloudWatch metrics for failed transactions
            # cloudwatch.put_metric_data(
            #     MetricData=[
            #         {
            #             'MetricName': 'FailedTransactions',
            #             'Unit': 'Count',
            #             'Value': 1
            #         },
            #     ],
            #     Namespace='BankingApp/Transactions'
            # )

            return {
                'statusCode': 400,
                'body': json.dumps(f"Transaction failed: {str(e)}")
            }

    return {
        'statusCode': 200,
        'body': json.dumps('Transaction processed successfully')
    }

