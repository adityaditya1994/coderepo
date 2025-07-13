
path = f'dbfs:/mnt/s3mount1903/databricks_output/test_output.parquet/'

# step 1: data read
df_bronze = spark.read.parquet(path)

display(df_bronze)

## bronze layer -- write this data 

df_bronze.write.mode('overwrite').format('parquet').save( f'dbfs:/mnt/s3mount1903/bronze_layer/clickstream_raw_data.parquet/')


## silver layer 


from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType, LongType, IntegerType, DoubleType

spark = SparkSession.builder.appName("ClickstreamETL").getOrCreate()


campaign_data = [
    ("email", "retention"),
    ("facebook", "acquisition"),
    ("google", "paid_search"),
    ("twitter", "awareness")
]

campaign_df = spark.createDataFrame(campaign_data, ["traffic_source", "campaign_type"])

bronze_df = spark.read.parquet(f'dbfs:/mnt/s3mount1903/bronze_layer/clickstream_raw_data.parquet/')



silver_df = bronze_df.select('device', 'ecommerce.unit','ecommerce.price', 'event_name', 'traffic_source'  ).filter(' device is not null and unit is not null and price is not null and event_name is not null and traffic_source is not null  ') 



# display(silver_df)
# Join with campaign mapping
silver_enriched_df = silver_df.join(campaign_df, on="traffic_source", how="left")

# # Save to silver
silver_enriched_df.write.mode('overwrite').format('parquet').save( f'dbfs:/mnt/s3mount1903/silver_layer/clickstream_silver_data.parquet/')


##### gold layer 



silver_df = spark.read.parquet(f'dbfs:/mnt/s3mount1903/silver_layer/clickstream_silver_data.parquet/')

# display(silver_df)

# Total sales = price * unit
sales_df = silver_df.withColumn("sales_amount", col("price") * col("unit"))

# display(sales_df)

# # 1. Sales by device
sales_by_device = sales_df.groupBy("device").sum("sales_amount").withColumnRenamed("sum(sales_amount)", "total_sales").sort('total_sales')

# display(sales_by_device)

# # 2. Sales by traffic source
sales_by_source = sales_df.groupBy("traffic_source").sum("sales_amount").withColumnRenamed("sum(sales_amount)", "total_sales").sort('total_sales')

# display(sales_by_source)


# # 3. Total orders
orders_df = silver_df.filter(col("event_name") == "order placed") \
    .groupBy("device", "traffic_source") \
    .count() \
    .withColumnRenamed("count", "total_orders").sort('total_orders')

# display(orders_df)

# # 4. Conversion rate
from pyspark.sql.functions import count, when

conversion_df = silver_df.groupBy("device").agg(
    count(when(col("event_name") == "order placed", True)).alias("orders"),
    count(when(col("event_name") == "add to cart", True)).alias("carts")
).withColumn("conversion_rate", col("orders") / col("carts"))


# display(conversion_df)

# # Save KPI to gold
sales_by_device.coalesce(1).write.mode('overwrite').format('csv').save( f'dbfs:/mnt/s3mount1903/gold_layer/kpi_sales_by_device.csv/')
sales_by_source.coalesce(1).write.mode('overwrite').format('csv').save( f'dbfs:/mnt/s3mount1903/gold_layer/kpi_sales_by_traffic.csv/')
orders_df.coalesce(1).write.mode('overwrite').format('csv').save( f'dbfs:/mnt/s3mount1903/gold_layer/kpi_orders.csv/')
conversion_df.coalesce(1).write.mode('overwrite').format('csv').save( f'dbfs:/mnt/s3mount1903/gold_layer/kpi_conversion.csv/')  
