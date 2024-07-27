df = spark.read.option('header', True).csv('dbfs:/databricks-datasets/online_retail/data-001/data.csv')
