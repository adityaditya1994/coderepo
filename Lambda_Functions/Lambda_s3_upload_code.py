import csv
import tempfile
import boto3
# from faker import Faker
import random

def generate_random_data(num_rows):
    data = [["Id", "Name", "Age", "Salary"]]
    
    for i in range(num_rows):
        data.append([
            i + 1,           # Id
            'John',     # Name
            i+10,  # Age (random between 20 and 60)
            f"{random.randint(50, 150)}K"  # Salary (random between 50K and 150K)
        ])
    
    return data


def lambda_handler(event, context):
    # Generate random CSV data
    num_rows = 5  # You can customize the number of rows
    csv_data = generate_random_data(num_rows)

    # Create a temporary file to store the CSV data
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    with open(temp_file.name, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(csv_data)

    # Define the S3 bucket and file name
    s3_bucket = 'ahs-datalake-2709'
    s3_file_key = 'input_files/employee_customer_1.csv'  # Customize the folder and file name

    # Upload the CSV file to S3
    s3 = boto3.client('s3')
    s3.upload_file(temp_file.name, s3_bucket, s3_file_key)

    return {
        'statusCode': 200,
        'body': 'CSV file with random data uploaded to S3 successfully'
    }
