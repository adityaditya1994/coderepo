import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
args = getResolvedOptions(sys.argv, ['JOB_NAME'])

# Define source database and table
source_database = "source_db"
source_table = "source_table"

# Define bucket path
bucket_path = "s3://your-bucket-name/path/"

# Create dynamic frame from source table
dyf = glueContext.create_dynamic_frame.from_catalog(database=source_database, table_name=source_table)

# Use case 1: Per Outlet Location Type and outlet Size Sales and count
outlet_sales_count = dyf.groupby(["Outlet_Location_Type", "Outlet_Size"]).agg({"Item_Outlet_Sales": "sum", "*": "count"})
outlet_sales_count.toDF().write.mode("overwrite").parquet(bucket_path + "outlet_sales_count")

# Use case 2: Per Outlet Location Type and Size and item type sales and count
item_sales_count = dyf.groupby(["Outlet_Location_Type", "Outlet_Size", "Item_Type"]).agg({"Item_Outlet_Sales": "sum", "*": "count"})
item_sales_count.toDF().write.mode("overwrite").parquet(bucket_path + "item_sales_count")

# Use case 3: Sales per item type
sales_per_item_type = dyf.groupby("Item_Type").agg({"Item_Outlet_Sales": "sum"})
sales_per_item_type.toDF().write.mode("overwrite").parquet(bucket_path + "sales_per_item_type")

# Commit the job
job.commit()
