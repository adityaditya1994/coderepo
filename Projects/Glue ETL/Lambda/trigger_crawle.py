import json
import boto3
glue=boto3.client('glue')

def trigger_crawler():
    print('Crawler to start')
    response = glue.start_crawler(
    Name='ahs-glue-crawler-sales-data-2604'
    )
    print('Crawler started')
    return response

def trigger_glue_job():
    response = glue.start_job_run(JobName = "sales_ui_2804")
    print("Lambda Invoke Glue job")


def lambda_handler(event, context):

    if 'Records' in event:
        print(trigger_crawler())
    elif event.get('source') == 'aws.glue':
        print(trigger_glue_job())
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

