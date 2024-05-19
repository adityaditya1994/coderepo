Build an Automated⚙️ Serverless DataLake —

Often Data Engineering Teams spend most of their time on building and optimizing extract, transform, and load (ETL) pipelines. Automating the entire process can reduce the time to value and cost of operations.
This project explains how to create a fully automated data cataloging and ETL pipeline to transform your data.
What will you learn?
✅ Python
✅ Amazon S3 trigger to invoke a Lambda function
✅ Glue Crawler
✅ Creating a CloudWatch Events Rule that triggers on an Event
✅ Writing ETL job using PySpark and storing data on S3
✅ Setting up notification for AWS Glue jobs success/failure using SNS


Note: How crawler helps -
    - Suppose today my file is command delimited, Glue can manage. But suppose it changed to pipe in future, the pipeline will fail. But if we have crawler, it auto detects these changes and load the data into catalog tables.

Analytics:
        a. Per Outlet Location Type and outlet Size Sales and count
        b. Per Outlet Location Type and Size and item type sales and count
        c. Sales per  item type


Architecture 1:
Purely on AWS

![alt text](image-1.png)