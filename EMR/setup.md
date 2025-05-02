Variable Setup:

export SRC_DIR=s3://ahs-emr-bucket-1508/input_data/
A export ENVIRON=PROD
B export SRC_FILE_PATTERN=2021-01-13
C export SRC_FILE_FORMAT=JSON
D export TGT_DIR=s3://ahs-emr-bucket-1508/target_folder/
E  export TGT_FILE_FORMAT=json

Spark COmmand: 
spark-submit --master yarn --py-files spark_code.zip app.py



Note: Please change the bucket name as per your own bucket. 

