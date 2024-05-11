import os
import pandas as pd
import boto3

table_name = os.environ['table_name']

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

s3 = boto3.client('s3')

def calculate_net_salary(salary):
    # Simple transformation: Subtract 10% from Salary to get NetSalary
    
    return str(int(salary[:-1]) * 0.9)+'K'

def lambda_handler(event, context):
    # Get the S3 bucket and file name from the event
    try:
        s3_bucket = event['Records'][0]['s3']['bucket']['name']
        s3_file_key = event['Records'][0]['s3']['object']['key']
    
        # Read data from the CSV file in S3 using Pandas
        csv_obj = s3.get_object(Bucket=s3_bucket, Key=s3_file_key)
        df = pd.read_csv(csv_obj['Body'])
    
        # Apply transformation and insert data into DynamoDB
        for index, row in df.iterrows():
            # Simple transformation: Subtract 10% from Salary to get NetSalary
            net_salary = calculate_net_salary(row['Salary'])
    
            # Customize this part to match your CSV file structure and transformation requirements
            item = {
                'Id': str(row['Id']),
                'Name': row['Name'],
                'Age': int(row['Age']),
                'Salary': row['Salary'],
                'NetSalary': net_salary  # Adding the calculated field
            }

            table.put_item(Item=item)
    
        return {
            'statusCode': 200,
            'body': 'Data with transformation inserted into DynamoDB successfully'
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        raise e
