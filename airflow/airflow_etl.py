from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SQLExecuteQueryOperator
from datetime import datetime # CORRECTED: Import datetime directly
# REMOVED: from airflow.utils.dates import days_ago (This is deprecated in Airflow 3.0)
from airflow.hooks.base import BaseHook # ADDED: For securely getting connection details in PythonOperators

import pandas as pd
from sqlalchemy import create_engine

# Snowflake connection ID - ensure this is configured in Airflow UI (Admin -> Connections)
SNOWFLAKE_CONN_ID = "snowflake-connection"

# Define the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
}

with DAG(
    "A_etl_snowflake",
    default_args=default_args,
    description="E-commerce ETL pipeline using PythonOperator and SQLExecuteQueryOperator",
    schedule=None, # Set to a cron string (e.g., '0 0 * * *' for daily) or timedelta for scheduled runs. None means manual triggers only.
    start_date=datetime(2025, 6, 1), # CORRECTED: Use a fixed datetime object. Airflow handles subsequent runs.
    catchup=False,
):

    import snowflake.connector
        
    # Retrieve connection details from Airflow Connection
    account = ''  # Your account identifier
    user = ''             # Your username
    password = ''     # Your password (replace with actual password)
    warehouse = 'AHS_SNOWFLAKE_WH'   # Your warehouse name
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

    def test_airflow():
        """
        Tests the connection to Snowflake and fetches sample data.
        RECOMMENDATION: Use Airflow Connections to retrieve credentials securely.
        """
        try:
            # Execute a query
            print("Executing test query on Snowflake...")
            cur.execute("SELECT CURRENT_VERSION() AS SNOWFLAKE_VERSION, CURRENT_TIMESTAMP() AS CURRENT_TIME;") 

            # Fetch the results
            results = cur.fetchall()

            # Print the results
            print("Snowflake test query results:")
            for row in results:
                print(row)

        except Exception as e:
            print(f"Error connecting to Snowflake or executing query: {e}")
            raise # Re-raise the exception to fail the task in Airflow
        finally:
            # Close the cursor and connection
            if cur:
                cur.close()
            if conn:
                conn.close()
        print("Snowflake connection test completed.")

    load_to_bronze_sql = """

    USE DATABASE ahs_airflow_data ;
    USE SCHEMA ahs_airflow_schema ;

    CREATE OR REPLACE TABLE landing_new AS
    SELECT 
    order_id,
    product_id,
    customer_id,
    quantity,
    (quantity * price_per_unit) AS total_price,
    DATE(order_date) AS order_date,
    region
    FROM landing_table;

    INSERT OVERWRITE INTO bronze_table
    SELECT 
    order_id,
    product_id,
    customer_id,
    quantity,
    total_price,
    order_date,
    region,
    CURRENT_TIMESTAMP() AS load_timestamp
    FROM landing_new;


    """

    # Define SQL transformations in Snowflake
    # This SQL will be executed directly by the Snowflake hook/operator
    bronze_to_aggregated_sql = """
    USE DATABASE ahs_airflow_data ;
    USE SCHEMA ahs_airflow_schema ;

    CREATE TABLE IF NOT EXISTS final_aggregated_table (
        product_id VARCHAR,
        region VARCHAR,
        month VARCHAR,
        total_sales FLOAT,
        total_quantity INTEGER
    );

    INSERT OVERWRITE INTO final_aggregated_table (product_id, region, month, total_sales, total_quantity)
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
    # provide_context=True is generally not needed unless you are explicitly
    # accessing kwargs['ti'], kwargs['dag_run'], etc., within your python_callable.
    # For these functions, it's not strictly necessary.
    snowflake_test = PythonOperator(
        task_id="snowflake_test_connection", # Renamed for clarity
        python_callable=test_airflow,
        # provide_context=True # Can be removed if context isn't used
    )

    load_to_bronze_task = SQLExecuteQueryOperator(
        task_id="load_to_bronze",
        conn_id=SNOWFLAKE_CONN_ID,
        sql=load_to_bronze_sql,
    )

    # bronze_to_aggregated_task = SQLExecuteQueryOperator(
    #     task_id="bronze_to_aggregated",
    #     conn_id=SNOWFLAKE_CONN_ID,
    #     sql=bronze_to_aggregated_sql,
    #     # autocommit=True # Often helpful for DDL/DML statements
    # )

# Task dependencies
#snowflake_test >> load_to_bronze_task >> bronze_to_aggregated_task
snowflake_test >> load_to_bronze_task

