Create Storage Integration:

CREATE or replace STORAGE INTEGRATION ahs_sales_s3
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = 'S3'
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::891377344475:role/ahs-snowflake-role-2'
  ENABLED = TRUE
  STORAGE_ALLOWED_LOCATIONS = ('s3://ahs-glue-project-bucket-2604/')
  ;

Verify Integration:

show integrations ;
desc integration AHS_SALES_S3 ;


Create File Format:
 
  CREATE OR REPLACE FILE FORMAT my_csv_format
  TYPE = CSV
  FIELD_DELIMITER = ','
  SKIP_HEADER = 1
  TRIM_SPACE = TRUE
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'

Create Stage:

CREATE or replace STAGE ahs_sales_s3
URL = 's3://ahs-glue-project-bucket-2604/'
STORAGE_INTEGRATION = ahs_sales_s3
file_format = my_csv_format
;

Verify Stages: 

show stages ;
desc stage ahs_sales_s3 ;



Verify the data present in S3 bucket: 

list @ahs_sales_s3 ;
list @ahs_sales_s3/target_data/Location_Outlet/ ;


select $1, $2, $3, $4, $5 from @ahs_sales_s3/src_files/sales/Train.csv (file_format => my_csv_format ) ;



