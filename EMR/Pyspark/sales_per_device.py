from pyspark.sql.functions import *
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, MapType

df = spark.read.json('/mnt/s3dataread/databricks_input/clickstream_data_with_nulls.json')
# display(df.select('ecommerce.price'))
#display(df)
ecommerce_schema = StructType([
    StructField("price", IntegerType(), True),
    StructField("unit", IntegerType(), True)
])


geo_schema = StructType([
    StructField("city", StringType(), True),
    StructField("state", StringType(), True)
])

# Convert 'ecommerce' column from string to dictionary (struct type)
df2 = df.withColumn("ecommerce", from_json(col("ecommerce"), ecommerce_schema)).withColumn("geo", from_json(col("geo"), geo_schema))
df3 = df2.select('device', 'ecommerce.price', 'ecommerce.unit')
#display(df3)
df4 = df3.filter(" device is not null ").filter(" price is not null").filter(" unit is not null")
#display(df4)
df5 = df4.withColumn("revenue", col('price')*col('unit'))
#display(df5)
df6 = df5.groupBy('device').sum('revenue')
#display(df6)
df7 = df5.groupBy('device').avg('revenue')
#display(df7)

df_agg = df5.groupBy('device').agg(sum('revenue').alias('sum_rev'), avg('revenue').alias('avg_rev'))
display(df_agg)
