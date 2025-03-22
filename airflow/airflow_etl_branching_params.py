from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.dates import days_ago
import pandas as pd
from sqlalchemy import create_engine

# Snowflake connection ID
SNOWFLAKE_CONN_ID = "snowflake-connection"

# Database connection for pandas transformations
SNOWFLAKE_SQLALCHEMY_URI = f'snowflake://ADITYA2203:XXXXXXX@MENPHPM-SO19591/ahs_airflow_data/ahs_airflow_schema?warehouse=COMPUTE_WH'

# Define the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
}
with DAG(
    "snowflake_params_dag",
    default_args=default_args,
    description="E-commerce ETL pipeline using PythonOperator and SQLExecuteQueryOperator",
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
    params = {"cleanup" : "",
               "datasetup": "" 
                }
):

    def test_airflow():
        import snowflake.connector
        # Define your connection parameters
        account = 'MENPHPM-SO19591'  # Your account identifier
        user = 'ADITYA2203'             # Your username
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
            cur.execute(" select current_timestamp ")  # Replace with your table name

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
        
    def branch_cleanup_func(**kwargs):
        """Decide whether to run the cleanup task based on the run_cleanup flag."""
        conf = kwargs['dag_run'].conf
        run_cleanup = conf.get('cleanup', False)  # Default to False if not provided
        if run_cleanup:
            return "clean_up_task"
        return "skip_cleanup"

    def branch_insert_func(**kwargs):
        """Decide whether to run the insert task based on the run_insert flag."""
        conf = kwargs['dag_run'].conf
        run_insert = conf.get('datasetup', False)  # Default to False if not provided
        if run_insert:
            return "insert_task"
        return "skip_insert"

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
    
    
    cleanup_sql =  """
    use database ahs_airflow_data ;
    use schema ahs_airflow_schema ;
    truncate table bronze_table ;
    truncate table landing_table ;
    truncate table final_aggregated_table ;
    """
    
    data_setup_sql = """
    use database ahs_airflow_data ;
    use schema ahs_airflow_schema ;
    CREATE TABLE if not exists landing_table (
    order_id STRING,
    product_id STRING,
    customer_id STRING,
    quantity INT,
    price_per_unit FLOAT,
    order_date TIMESTAMP,
    region STRING
    );
    
    CREATE TABLE if not exists bronze_table (
    order_id STRING,
    product_id STRING,
    customer_id STRING,
    quantity INT,
    total_price FLOAT,
    order_date DATE,
    region STRING
    );


    CREATE TABLE if not exists final_aggregated_table (
        product_id STRING,
        region STRING,
        month STRING,
        total_sales FLOAT,
        total_quantity INT
    );

    
    
    call InsertRecords();    
    """

    # Define tasks
    snowflake_test = PythonOperator(
        task_id="snowflake_test",
        python_callable=test_airflow,
        provide_context=True,
        trigger_rule="one_success"
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
    
    skip_cleanup = DummyOperator(task_id="skip_cleanup")
    skip_insert = DummyOperator(task_id="skip_insert")
    
    clean_up_task = SQLExecuteQueryOperator(
        task_id="clean_up_task",
        conn_id=SNOWFLAKE_CONN_ID,
        sql=cleanup_sql
    )
    
    
    insert_task = SQLExecuteQueryOperator(
        task_id="insert_task",
        conn_id=SNOWFLAKE_CONN_ID,
        sql=data_setup_sql
    )
    

    # Branching tasks to decide whether to run cleanup and insert
    branch_cleanup = BranchPythonOperator(
        task_id="branch_cleanup",
        python_callable=branch_cleanup_func,
        provide_context=True
    )

    branch_insert = BranchPythonOperator(
        task_id="branch_insert",
        python_callable=branch_insert_func,
        provide_context=True,
        trigger_rule="one_success"
    )

    # Task dependencies
    # First, decide if cleanup should run
    branch_cleanup >> [clean_up_task, skip_cleanup]

    # Converge after cleanup (or skipping it)
    clean_up_task >> branch_insert
    skip_cleanup >> branch_insert

    # After cleanup convergence, decide if insert should run
    branch_insert >> [insert_task, skip_insert]

    # Converge after insert (or skipping it)
    insert_task >> snowflake_test
    skip_insert >> snowflake_test

    # Main pipeline starts after insert convergence
    snowflake_test >> extract_transform_task >> load_to_bronze_task >> bronze_to_aggregated_task
