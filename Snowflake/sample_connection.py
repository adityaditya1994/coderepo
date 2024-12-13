import snowflake.connector

# Define your connection parameters
account = 'KRMPROT-HB28498'  # Your account identifier
user = 'ADITYA121224'             # Your username
password = 'XXXXXXX'     # Your password (replace with actual password)
warehouse = 'COMPUTE_WH'   # Your warehouse name
database = 'ahs_airflow_data'     # Your database name
schema = 'ahs_airflow_schema'         # Your schema name

# Establish a connection to Snowflake
conn = snowflake.connector.connect(
    user=user,
    password=password,
    account=account,
    warehouse=warehouse,
    database=database,
    schema=schema
)

# Create a cursor object
cur = conn.cursor()

try:
    # Execute a query
    cur.execute("SELECT * FROM landing_table LIMIT 10")  # Replace with your table name

    # Fetch the results
    results = cur.fetchall()

    # Print the results
    for row in results:
        print(row)

finally:
    # Close the cursor and connection
    cur.close()
    conn.close()
