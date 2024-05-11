import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as SqlFuncs

def sparkAggregate(glueContext, parentFrame, groups, aggs, transformation_ctx) -> DynamicFrame:
    aggsFuncs = []
    for column, func in aggs:
        aggsFuncs.append(getattr(SqlFuncs, func)(column))
    result = parentFrame.toDF().groupBy(*groups).agg(*aggsFuncs) if len(groups) > 0 else parentFrame.toDF().agg(*aggsFuncs)
    return DynamicFrame.fromDF(result, glueContext, transformation_ctx)

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Script generated for node AWS Glue Data Catalog
AWSGlueDataCatalog_node1714316900584 = glueContext.create_dynamic_frame.from_catalog(database="ahs-glue-db-1804", table_name="salesdata_sales", transformation_ctx="AWSGlueDataCatalog_node1714316900584")

# Script generated for node Select Fields
SelectFields_node1714317004719 = SelectFields.apply(frame=AWSGlueDataCatalog_node1714316900584, paths=["outlet_size", "outlet_location_type", "item_outlet_sales", "outlet_type", "item_type"], transformation_ctx="SelectFields_node1714317004719")

# Script generated for node Location_Outlet
Location_Outlet_node1715410466415 = sparkAggregate(glueContext, parentFrame = SelectFields_node1714317004719, groups = ["outlet_location_type", "outlet_size"], aggs = [["item_outlet_sales", "sum"], ["item_type", "count"]], transformation_ctx = "Location_Outlet_node1715410466415")

# Script generated for node salesPerItemType_agg
salesPerItemType_agg_node1714317101715 = sparkAggregate(glueContext, parentFrame = SelectFields_node1714317004719, groups = ["item_type"], aggs = [["item_outlet_sales", "sum"], ["item_type", "count"]], transformation_ctx = "salesPerItemType_agg_node1714317101715")

# Script generated for node outlet_location_item_agg
outlet_location_item_agg_node1714317062851 = sparkAggregate(glueContext, parentFrame = SelectFields_node1714317004719, groups = ["outlet_type", "outlet_location_type", "item_type"], aggs = [["item_outlet_sales", "sum"], ["item_type", "count"]], transformation_ctx = "outlet_location_item_agg_node1714317062851")

# Script generated for node Change Schema
ChangeSchema_node1715413078489 = ApplyMapping.apply(frame=Location_Outlet_node1715410466415, mappings=[("outlet_location_type", "string", "outlet_location_type", "string"), ("outlet_size", "string", "outlet_size", "string"), ("`sum(item_outlet_sales)`", "double", "Total_Sales", "double"), ("`count(item_type)`", "long", "Item_Sold", "long")], transformation_ctx="ChangeSchema_node1715413078489")

# Script generated for node salesPerItemType_changeSchema
salesPerItemType_changeSchema_node1714541631930 = ApplyMapping.apply(frame=salesPerItemType_agg_node1714317101715, mappings=[("item_type", "string", "item_type", "string"), ("`sum(item_outlet_sales)`", "double", "Total_Outlet_Sales", "double"), ("`count(item_type)`", "long", "Count_Items_Sold", "long")], transformation_ctx="salesPerItemType_changeSchema_node1714541631930")

# Script generated for node Change Schema
ChangeSchema_node1715410295102 = ApplyMapping.apply(frame=outlet_location_item_agg_node1714317062851, mappings=[("outlet_type", "string", "outlet_type", "string"), ("outlet_location_type", "string", "outlet_location_type", "string"), ("item_type", "string", "item_type", "string"), ("`sum(item_outlet_sales)`", "double", "Total_Sales", "double"), ("`count(item_type)`", "long", "Total_Item_Sold", "long")], transformation_ctx="ChangeSchema_node1715410295102")

# Script generated for node Amazon S3
AmazonS3_node1715413112066 = glueContext.write_dynamic_frame.from_options(frame=ChangeSchema_node1715413078489, connection_type="s3", format="csv", connection_options={"path": "s3://ahs-glue-project-bucket-2604/target_data/Location_Outlet/", "partitionKeys": []}, transformation_ctx="AmazonS3_node1715413112066")

# Script generated for node Amazon S3
AmazonS3_node1714543899158 = glueContext.write_dynamic_frame.from_options(frame=salesPerItemType_changeSchema_node1714541631930, connection_type="s3", format="csv", connection_options={"path": "s3://ahs-glue-project-bucket-2604/target_data/sales_item_type/", "partitionKeys": []}, transformation_ctx="AmazonS3_node1714543899158")

# Script generated for node Amazon S3
AmazonS3_node1715410380482 = glueContext.write_dynamic_frame.from_options(frame=ChangeSchema_node1715410295102, connection_type="s3", format="csv", connection_options={"path": "s3://ahs-glue-project-bucket-2604/target_data/outlet_location_item/", "partitionKeys": []}, transformation_ctx="AmazonS3_node1715410380482")

job.commit()