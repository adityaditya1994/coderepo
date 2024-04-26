import json
import boto3
glue=boto3.client('glue')

def trigger_crawler:
    response = glue.start_crawler(
    Name='{Put the Name of the Glue Crawler here}'
    )
    return response

def trigger_glue_job():
    response = glue.start_job_run(JobName = "{Put the Glue ETL Job name here}")
    print("Lambda Invoke Glue job")


def lambda_handler(event, context):
    if trigger_type == 'crawler':
        trigger_crawler
    elif trigger_type == 'glue_job':
        trigger_glue_job() 
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
    return response

