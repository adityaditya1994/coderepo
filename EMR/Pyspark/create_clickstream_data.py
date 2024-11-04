import pandas as pd
import random
import json
from datetime import datetime, timedelta

# Function to generate clickstream data
def generate_clickstream_data(num_records):
    # Parameters
    devices = ['mac', 'iphone', 'chrome', 'android', 'unix']
    event_names = ['warranty', 'add to cart', 'order placed']
    traffic_sources = ['google', 'facebook', 'twitter', 'email', 'direct']

    # Function to generate random timestamps
    def random_timestamp(start, end):
        return int((start + (end - start) * random.random()).timestamp() * 1_000_000)

    # Generate data
    data = []
    start_time = datetime.now() - timedelta(days=30)  # Start time 30 days ago
    for _ in range(num_records):
        # Randomly decide whether to assign None (null) or a value for certain fields
        device = random.choice(devices + [None] * 2)  # 2 chances out of 7 to be None
        ecommerce = json.dumps({"price": random.randint(50, 200), "unit": random.randint(1, 20)}) if random.random() > 0.2 else None  # 20% chance to be None
        event_name = random.choice(event_names)
        
        # Generate timestamps
        event_previous_timestamp = random_timestamp(start_time, datetime.now())
        event_timestamp = random_timestamp(start_time, datetime.now())
        
        geo = json.dumps({
            "city": random.choice(["Montrose", "Detroit", "Chicago", "New York", "Los Angeles"]),
            "state": random.choice(["MI", "IL", "NY", "CA", "TX"])
        }) if random.random() > 0.2 else None  # 20% chance to be None
        
        items = json.dumps([])  # Empty list for items
        traffic_source = random.choice(traffic_sources + [None] * 2) if random.random() > 0.2 else None  # 20% chance to be None
        
        user_first_touch_timestamp = random_timestamp(start_time, datetime.now())
        user_id = f"UA{random.randint(100000000, 999999999)}"
        
        # Append record to data list
        data.append([
            device,
            ecommerce,
            event_name,
            event_previous_timestamp,
            event_timestamp,
            geo,
            items,
            traffic_source,
            user_first_touch_timestamp,
            user_id
        ])

    # Create DataFrame
    columns = [
        "device",
        "ecommerce",
        "event_name",
        "event_previous_timestamp",
        "event_timestamp",
        "geo",
        "items",
        "traffic_source",
        "user_first_touch_timestamp",
        "user_id"
    ]
    df = pd.DataFrame(data, columns=columns)

    return df

# User-defined number of rows
df = generate_clickstream_data(1000)

# Convert the Pandas DataFrame to a Spark DataFrame
spark_df = spark.createDataFrame(df)

# Save the Spark DataFrame to S3 using the mounted path
output_file_path = '/mnt/s3dataread/databricks_input/clickstream_data_with_nulls.json'
spark_df.write.mode('overwrite').json(output_file_path)

# print(f"Sample clickstream data with null values generated and saved to {output_file_path}.")
