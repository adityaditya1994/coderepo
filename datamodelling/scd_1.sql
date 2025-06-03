-- Create a database (if it doesn't exist)
CREATE DATABASE IF NOT EXISTS SCD_DEMO_DB;

-- Create a schema (if it doesn't exist)
CREATE SCHEMA IF NOT EXISTS DEMO_SCHEMA;

-- Use the database and schema
USE DATABASE SCD_DEMO_DB;
USE SCHEMA DEMO_SCHEMA;

-- Create a raw source table to simulate incoming product data
CREATE OR REPLACE TABLE RAW_PRODUCTS (
    PRODUCT_ID VARCHAR(10),
    PRODUCT_NAME VARCHAR(100),
    CATEGORY VARCHAR(50),
    PRICE DECIMAL(10,2),
    LAST_UPDATED_TIMESTAMP TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() -- To track when the source record was last "updated"
);

-- Insert some initial sample data into the raw source table
INSERT INTO RAW_PRODUCTS (PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE) VALUES
('P001', 'Laptop Pro 15', 'Electronics', 1200.00),
('P002', 'Wireless Mouse', 'Accessories', 25.00),
('P003', 'Office Chair Deluxe', 'Furniture', 150.00);

-- View the initial raw data
SELECT * FROM RAW_PRODUCTS ORDER BY PRODUCT_ID;

CREATE OR REPLACE TABLE DIM_PRODUCTS_SCD1 (
    PRODUCT_ID VARCHAR(10) PRIMARY KEY, -- Natural Key
    PRODUCT_NAME VARCHAR(100),
    CATEGORY VARCHAR(50),
    PRICE DECIMAL(10,2),
    DW_LAST_UPDATED_TIMESTAMP TIMESTAMP_NTZ -- Timestamp of last update in the DWH
);

-- Initial load
INSERT INTO DIM_PRODUCTS_SCD1 (PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE, DW_LAST_UPDATED_TIMESTAMP)
SELECT
    PRODUCT_ID,
    PRODUCT_NAME,
    CATEGORY,
    PRICE,
    CURRENT_TIMESTAMP() -- Set DWH update timestamp
FROM RAW_PRODUCTS;

-- View the SCD1 dimension table after initial load
SELECT * FROM DIM_PRODUCTS_SCD1 ORDER BY PRODUCT_ID;



UPDATE RAW_PRODUCTS
SET PRICE = 1250.00, LAST_UPDATED_TIMESTAMP = CURRENT_TIMESTAMP()
WHERE PRODUCT_ID = 'P001';

UPDATE RAW_PRODUCTS
SET PRODUCT_NAME = 'Ergonomic Wireless Mouse', LAST_UPDATED_TIMESTAMP = CURRENT_TIMESTAMP()
WHERE PRODUCT_ID = 'P002';

-- Simulate a new product arrival
INSERT INTO RAW_PRODUCTS (PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE, LAST_UPDATED_TIMESTAMP) VALUES
('P004', 'Gaming Keyboard', 'Accessories', 75.00, CURRENT_TIMESTAMP());

-- View the updated raw data
SELECT * FROM RAW_PRODUCTS ORDER BY PRODUCT_ID;



MERGE INTO DIM_PRODUCTS_SCD1 AS target
USING (
    SELECT
        PRODUCT_ID,
        PRODUCT_NAME,
        CATEGORY,
        PRICE,
        LAST_UPDATED_TIMESTAMP AS SOURCE_LAST_UPDATED_TIMESTAMP
    FROM RAW_PRODUCTS
) AS source
ON target.PRODUCT_ID = source.PRODUCT_ID
WHEN MATCHED AND (
       target.PRODUCT_NAME <> source.PRODUCT_NAME OR
       target.CATEGORY <> source.CATEGORY OR
       target.PRICE <> source.PRICE
    ) THEN UPDATE SET -- If product exists and any attribute has changed, update it
        target.PRODUCT_NAME = source.PRODUCT_NAME,
        target.CATEGORY = source.CATEGORY,
        target.PRICE = source.PRICE,
        target.DW_LAST_UPDATED_TIMESTAMP = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT ( -- If product does not exist in dimension, insert it
    PRODUCT_ID,
    PRODUCT_NAME,
    CATEGORY,
    PRICE,
    DW_LAST_UPDATED_TIMESTAMP
) VALUES (
    source.PRODUCT_ID,
    source.PRODUCT_NAME,
    source.CATEGORY,
    source.PRICE,
    CURRENT_TIMESTAMP()
);



truncate table 
SCD_DEMO_DB.DEMO_SCHEMA.DIM_PRODUCTS_SCD1 ;

truncate table 
SCD_DEMO_DB.DEMO_SCHEMA.RAW_PRODUCTS ;
