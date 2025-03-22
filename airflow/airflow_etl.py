from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SQLExecuteQueryOperator
from airflow.utils.dates import days_ago
import pandas as pd
from sqlalchemy import create_engine

# Snowflake connection ID
SNOWFLAKE_CONN_ID = "snowflake-connection"

# Database connection for pandas transformations
SNOWFLAKE_SQLALCHEMY_URI = f'snowflake://ADITYA2203:XXXXXXXXX@MENPHPM-SO19591/ahs_airflow_data/ahs_airflow_schema?warehouse=COMPUTE_WH'

# Define the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
}
with DAG(
    "snowflake_test_dag",
    default_args=default_args,
    description="E-commerce ETL pipeline using PythonOperator and SQLExecuteQueryOperator",
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
):

    def test_airflow():
        import snowflake.connector
        # Define your connection parameters
        account = 'MENPHPM-SO19591'  # Your account identifier
        user = 'ADITYA2203'             # Your username
        password = 'XXXXXXXXXX'     # Your password (replace with actual password)
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
    # Helper functions for PythonOperator
    def extract_transform(**kwargs):
        """Extract data from the landing table, perform transformations, and write to landing_new table."""
        # Snowflake connection using SQLAlchemy
        engine = create_engine(SNOWFLAKE_SQLALCHEMY_URI)
        query = "SELECT * FROM landing_table;"
        
        # Extract data from the landing table
        df = pd.read_sql(query, engine)

        # Perform transformations: calculate total price and simplify the date
        df['total_price'] = df['quantity'] * df['price_per_unit']
        df['order_date'] = pd.to_datetime(df['order_date']).dt.date

        # Save transformed data to a new table: landing_new
        df = df[['order_id', 'product_id', 'customer_id', 'quantity', 'total_price', 'order_date', 'region']]
        df.to_sql("landing_new", con=engine, if_exists="replace", index=False)

    def load_to_bronze(**kwargs):
        """Load transformed data from landing_new table into the bronze table."""
        # Snowflake connection using SQLAlchemy
        engine = create_engine(SNOWFLAKE_SQLALCHEMY_URI)
        
        # Read transformed data from landing_new table
        query = "SELECT * FROM landing_new;"
        df = pd.read_sql(query, engine)

        # Load data into the bronze table
        df.to_sql("bronze_table", con=engine, if_exists="replace", index=False)

    # Define SQL transformations in Snowflake
    bronze_to_aggregated_sql = """
    use database ahs_airflow_data ;
    use schema ahs_airflow_schema ;
    INSERT INTO final_aggregated_table
    SELECT
        product_id,
        region,
        TO_CHAR(order_date, 'YYYY-MM') AS month,
        SUM(total_price) AS total_sales,
        SUM(quantity) AS total_quantity
    FROM
        bronze_table
    GROUP BY
        product_id, region, TO_CHAR(order_date, 'YYYY-MM');
    """

    # Define tasks
    snowflake_test = PythonOperator(
        task_id="snowflake_test",
        python_callable=test_airflow,
        provide_context=True
    )

    extract_transform_task = PythonOperator(
        task_id="extract_and_transform",
        python_callable=extract_transform,
        provide_context=True
    )

    load_to_bronze_task = PythonOperator(
        task_id="load_to_bronze",
        python_callable=load_to_bronze,
        provide_context=True
    )

    bronze_to_aggregated_task = SQLExecuteQueryOperator(
        task_id="bronze_to_aggregated",
        conn_id=SNOWFLAKE_CONN_ID,
        sql=bronze_to_aggregated_sql
    )

# Task dependencies
    snowflake_test >> extract_transform_task >> load_to_bronze_task >> bronze_to_aggregated_task
