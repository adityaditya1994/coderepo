/* DDL for db, schema */
create or replace database ahs_airflow_data ;

use database ahs_airflow_data ;

create or replace schema ahs_airflow_schema ;

use schema ahs_airflow_schema ;

select *
from landing_table ;

/* DDL for tables */

CREATE TABLE landing_table (
    order_id STRING,
    product_id STRING,
    customer_id STRING,
    quantity INT,
    price_per_unit FLOAT,
    order_date TIMESTAMP,
    region STRING
);


CREATE OR REPLACE TABLE bronze_table (
    order_id STRING,
    product_id STRING,
    customer_id STRING,
    quantity INT,
    total_price FLOAT,
    order_date DATE,
    region STRING
);


CREATE TABLE final_aggregated_table (
    product_id STRING,
    region STRING,
    month STRING,
    total_sales FLOAT,
    total_quantity INT
);


/* code for procedure for creating sample records */

CREATE OR REPLACE PROCEDURE InsertRecords()
RETURNS STRING
LANGUAGE JAVASCRIPT
AS
$$
var sql_command = `INSERT INTO landing_table (order_id, product_id, customer_id, quantity, price_per_unit, order_date, region) VALUES `;
var values = [];

for (var i = 1; i <= 100000; i++) {
    var order_id = 'ORD' + i;
    var product_id = 'PROD' + (Math.floor(Math.random() * 1000) + 1);
    var customer_id = 'CUST' + (Math.floor(Math.random() * 500) + 1);
    var quantity = Math.floor(Math.random() * 10) + 1;
    var price_per_unit = (Math.random() * 99 + 1).toFixed(2);
    var order_date = new Date(Date.now() - Math.floor(Math.random() * 365 * 24 * 60 * 60 * 1000)).toISOString();
    var region = ['North', 'South', 'East', 'West'][Math.floor(Math.random() * 4)];

    values.push(`('${order_id}', '${product_id}', '${customer_id}', ${quantity}, ${price_per_unit}, '${order_date}', '${region}')`);

    // Batch insert every 1000 records to avoid exceeding statement length limits
    if (i % 1000 === 0) {
        sql_command += values.join(", ") + ";";
        var stmt = snowflake.createStatement({sqlText: sql_command});
        stmt.execute();
        sql_command = `INSERT INTO landing_table (order_id, product_id, customer_id, quantity, price_per_unit, order_date, region) VALUES `;
        values = [];
    }
}

// Insert any remaining records
if (values.length > 0) {
    sql_command += values.join(", ") + ";";
    var stmt = snowflake.createStatement({sqlText: sql_command});
    stmt.execute();
}

return 'Inserted 100,000 records successfully!';
$$
;
