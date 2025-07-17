from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg


# Function to generate customer data
def create_customer_data(num_rows, num_partitions):
    import random
    import pandas as pd
    from pyspark.sql.types import StructType, StructField, IntegerType, StringType

    schema = StructType([
        StructField("customer_id", IntegerType(), True),
        StructField("customer_name", StringType(), True),
        StructField("age", IntegerType(), True),
        StructField("country", StringType(), True)
    ])

    data = []
    names = ["Alice", "Bob", "Charlie", "David", "Eve"]
    countries = ["USA", "Canada", "UK", "Germany", "France"]
    for i in range(num_rows):
        data.append((i, random.choice(names), random.randint(18, 70), random.choice(countries)))

    pdf = pd.DataFrame(data, columns=["customer_id", "customer_name", "age", "country"])
    df = spark.createDataFrame(pdf, schema)
    return df.repartition(num_partitions)

# Generate sample datasets
num_rows_customers = 1000000  # Customer dataset
num_partitions_customers = 10



df_customers = create_customer_data(num_rows_customers, num_partitions_customers)


def create_sales_data(num_rows, num_partitions):
    import random
    import pandas as pd
    from pyspark.sql.types import StructType, StructField, IntegerType, FloatType, StringType

    schema = StructType([
        StructField("transaction_id", IntegerType(), True),
        StructField("customer_id", IntegerType(), True),
        StructField("amount", FloatType(), True),
        StructField("product", StringType(), True),
        StructField("category", StringType(), True)
    ])

    data = []
    products = ["Product1", "Product2", "Product3", "Product4", "Product5"]
    categories = ["Electronics", "Clothing", "Grocery", "Furniture", "Books"]
    for i in range(num_rows):
        data.append((i, random.randint(0, num_rows // 2), random.uniform(10.0, 1000.0), random.choice(products), random.choice(categories)))

    pdf = pd.DataFrame(data, columns=["transaction_id", "customer_id", "amount", "product", "category"])
    df = spark.createDataFrame(pdf, schema)
    return df.repartition(num_partitions)


num_rows_sales = 500000  # Sales dataset, larger to create more processing load
num_partitions_sales = 20

df_sales = create_sales_data(num_rows_sales, num_partitions_sales)

display(df_sales)




# Perform a join operation on customer_id
joined_df = df_customers.join(df_sales, df_customers.customer_id == df_sales.customer_id, "inner") ## wide


# Perform some transformations
filtered_df = joined_df.filter(col("amount") > 50) ## narrow


aggregated_df = filtered_df.groupBy("country", "category").agg(avg("amount").alias("avg_amount")) ## wide

display(aggregated_df)
