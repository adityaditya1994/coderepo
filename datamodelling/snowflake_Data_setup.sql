-- Module 1: Snowflake Setup & Raw Data Loading
-- Create a Virtual Warehouse (if you don't have one or want a dedicated one for this project)
-- This defines the compute resources for your queries.
CREATE WAREHOUSE IF NOT EXISTS ECOMMERCE_WH WITH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;

-- Use the created warehouse
USE WAREHOUSE ECOMMERCE_WH;

-- Create a Database for our project
CREATE DATABASE IF NOT EXISTS ECOMMERCE_DB;

-- Use the created database
USE DATABASE ECOMMERCE_DB;

-- Create schemas within the database
-- RAW: For initial, unnormalized data
CREATE SCHEMA IF NOT EXISTS RAW;
-- STAGING: For intermediate normalized tables before building the dimensional model
CREATE SCHEMA IF NOT EXISTS EXISTS STAGING;
-- ANALYTICS: For our final dimensional model (Star/Snowflake Schema)
CREATE SCHEMA IF NOT EXISTS ANALYTICS;

-- Step 2: Create a Raw Data Table
-- This table simulates a single, wide table from an operational system.
USE SCHEMA ECOMMERCE_DB.RAW;

CREATE OR REPLACE TABLE RAW_ECOM_SALES (
    ORDER_ID VARCHAR(50),
    ORDER_DATE DATE,
    CUSTOMER_ID VARCHAR(50),
    CUSTOMER_NAME VARCHAR(100),
    CUSTOMER_EMAIL VARCHAR(100),
    CUSTOMER_ADDRESS VARCHAR(255),
    PRODUCT_ID VARCHAR(50),
    PRODUCT_NAME VARCHAR(255),
    PRODUCT_CATEGORY VARCHAR(100),
    PRODUCT_PRICE DECIMAL(10, 2),
    QUANTITY INTEGER,
    TOTAL_PRICE DECIMAL(10, 2)
);

-- Insert sample data into the raw table
INSERT INTO RAW_ECOM_SALES (ORDER_ID, ORDER_DATE, CUSTOMER_ID, CUSTOMER_NAME, CUSTOMER_EMAIL, CUSTOMER_ADDRESS, PRODUCT_ID, PRODUCT_NAME, PRODUCT_CATEGORY, PRODUCT_PRICE, QUANTITY, TOTAL_PRICE) VALUES
('ORD001', '2024-01-10', 'CUST001', 'Alice Smith', 'alice@example.com', '123 Main St, Anytown', 'PROD001', 'Laptop', 'Electronics', 1200.00, 1, 1200.00),
('ORD001', '2024-01-10', 'CUST001', 'Alice Smith', 'alice@example.com', '123 Main St, Anytown', 'PROD002', 'Mouse', 'Electronics', 25.00, 2, 50.00),
('ORD002', '2024-01-11', 'CUST002', 'Bob Johnson', 'bob@example.com', '456 Oak Ave, Otherville', 'PROD003', 'Keyboard', 'Electronics', 75.00, 1, 75.00),
('ORD003', '2024-01-12', 'CUST001', 'Alice Smith', 'alice@example.com', '123 Main St, Anytown', 'PROD001', 'Laptop', 'Electronics', 1200.00, 1, 1200.00),
('ORD004', '2024-01-13', 'CUST003', 'Charlie Brown', 'charlie@example.com', '789 Pine Ln, Somewhere', 'PROD004', 'Desk Chair', 'Furniture', 150.00, 1, 150.00),
('ORD005', '2024-01-14', 'CUST002', 'Bob Johnson', 'bob@example.com', '456 Oak Ave, Otherville', 'PROD005', 'Headphones', 'Electronics', 90.00, 1, 90.00);

-- Verify raw data
SELECT * FROM RAW_ECOM_SALES;

----------------------------------------------------------------------------------------------------

-- Module 2: Data Modeling Concepts & Normalization

-- Step 1: Identify and Create 1NF Tables (already implied by creating a single table with atomic values)
-- The RAW_ECOM_SALES table is already in 1NF as it has atomic values and no repeating groups within a single row.
-- The next steps will focus on removing redundancy and partial/transitive dependencies.

-- Step 2: Normalize to 2NF and 3NF (creating separate tables for entities)
-- We will create tables for Customers, Products, Orders, and Order_Items in the STAGING schema.

USE SCHEMA ECOMMERCE_DB.STAGING;

-- Customer Table (3NF - no transitive dependencies, no partial dependencies on a composite key)
CREATE OR REPLACE TABLE CUSTOMERS (
    CUSTOMER_SK INTEGER IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key
    CUSTOMER_ID VARCHAR(50) UNIQUE, -- Natural Key
    CUSTOMER_NAME VARCHAR(100),
    CUSTOMER_EMAIL VARCHAR(100),
    CUSTOMER_ADDRESS VARCHAR(255)
);

-- Product Table (3NF)
CREATE OR REPLACE TABLE PRODUCTS (
    PRODUCT_SK INTEGER IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key
    PRODUCT_ID VARCHAR(50) UNIQUE, -- Natural Key
    PRODUCT_NAME VARCHAR(255),
    PRODUCT_CATEGORY VARCHAR(100),
    PRODUCT_PRICE DECIMAL(10, 2)
);

-- Order Table (3NF)
CREATE OR REPLACE TABLE ORDERS (
    ORDER_SK INTEGER IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key
    ORDER_ID VARCHAR(50) UNIQUE, -- Natural Key
    ORDER_DATE DATE,
    CUSTOMER_SK INTEGER -- Foreign Key to CUSTOMERS
);

-- Order_Items Table (3NF - breaking out line items from orders)
-- This table resolves the many-to-many relationship between orders and products.
CREATE OR REPLACE TABLE ORDER_ITEMS (
    ORDER_ITEM_SK INTEGER IDENTITY(1,1) PRIMARY KEY, -- Surrogate Key
    ORDER_SK INTEGER, -- Foreign Key to ORDERS
    PRODUCT_SK INTEGER, -- Foreign Key to PRODUCTS
    QUANTITY INTEGER,
    ITEM_TOTAL_PRICE DECIMAL(10, 2)
);

-- Populate the normalized tables from RAW_ECOM_SALES

-- Populate CUSTOMERS
INSERT INTO CUSTOMERS (CUSTOMER_ID, CUSTOMER_NAME, CUSTOMER_EMAIL, CUSTOMER_ADDRESS)
SELECT DISTINCT
    CUSTOMER_ID,
    CUSTOMER_NAME,
    CUSTOMER_EMAIL,
    CUSTOMER_ADDRESS
FROM ECOMMERCE_DB.RAW.RAW_ECOM_SALES;

-- Populate PRODUCTS
INSERT INTO PRODUCTS (PRODUCT_ID, PRODUCT_NAME, PRODUCT_CATEGORY, PRODUCT_PRICE)
SELECT DISTINCT
    PRODUCT_ID,
    PRODUCT_NAME,
    PRODUCT_CATEGORY,
    PRODUCT_PRICE
FROM ECOMMERCE_DB.RAW.RAW_ECOM_SALES;

-- Populate ORDERS
INSERT INTO ORDERS (ORDER_ID, ORDER_DATE, CUSTOMER_SK)
SELECT DISTINCT
    res.ORDER_ID,
    res.ORDER_DATE,
    c.CUSTOMER_SK
FROM ECOMMERCE_DB.RAW.RAW_ECOM_SALES res
JOIN CUSTOMERS c ON res.CUSTOMER_ID = c.CUSTOMER_ID;

-- Populate ORDER_ITEMS
INSERT INTO ORDER_ITEMS (ORDER_SK, PRODUCT_SK, QUANTITY, ITEM_TOTAL_PRICE)
SELECT
    o.ORDER_SK,
    p.PRODUCT_SK,
    res.QUANTITY,
    res.TOTAL_PRICE -- Note: In a real scenario, TOTAL_PRICE here would be QUANTITY * PRODUCT_PRICE for the line item
FROM ECOMMERCE_DB.RAW.RAW_ECOM_SALES res
JOIN ORDERS o ON res.ORDER_ID = o.ORDER_ID
JOIN PRODUCTS p ON res.PRODUCT_ID = p.PRODUCT_ID;

-- Verify normalized data
SELECT * FROM CUSTOMERS LIMIT 5;
SELECT * FROM PRODUCTS LIMIT 5;
SELECT * FROM ORDERS LIMIT 5;
SELECT * FROM ORDER_ITEMS LIMIT 5;

----------------------------------------------------------------------------------------------------

-- Module 3: Schema Design for Data Warehouses (Star & Snowflake Schema)

-- Step 1: Design and Implement Star Schema
-- We will create Dimension tables and a Fact table in the ANALYTICS schema.

USE SCHEMA ECOMMERCE_DB.ANALYTICS;

-- Dimension: DIM_CUSTOMER
CREATE OR REPLACE TABLE DIM_CUSTOMER (
    CUSTOMER_KEY INTEGER PRIMARY KEY, -- Surrogate Key for DW
    CUSTOMER_ID VARCHAR(50),
    CUSTOMER_NAME VARCHAR(100),
    CUSTOMER_EMAIL VARCHAR(100),
    CUSTOMER_ADDRESS VARCHAR(255)
);

-- Dimension: DIM_PRODUCT
CREATE OR REPLACE TABLE DIM_PRODUCT (
    PRODUCT_KEY INTEGER PRIMARY KEY, -- Surrogate Key for DW
    PRODUCT_ID VARCHAR(50),
    PRODUCT_NAME VARCHAR(255),
    PRODUCT_CATEGORY VARCHAR(100),
    PRODUCT_PRICE DECIMAL(10, 2)
);

-- Dimension: DIM_DATE (Simplified for this example, usually a robust date dimension is pre-built)
CREATE OR REPLACE TABLE DIM_DATE (
    DATE_KEY INTEGER PRIMARY KEY, -- YYYYMMDD
    FULL_DATE DATE,
    DAY_OF_WEEK VARCHAR(10),
    MONTH_NAME VARCHAR(10),
    QUARTER INTEGER,
    YEAR INTEGER
);

-- Populate DIM_DATE (for the dates present in our raw data)
INSERT INTO DIM_DATE (DATE_KEY, FULL_DATE, DAY_OF_WEEK, MONTH_NAME, QUARTER, YEAR)
SELECT DISTINCT
    TO_NUMBER(TO_CHAR(ORDER_DATE, 'YYYYMMDD')),
    ORDER_DATE,
    DAYNAME(ORDER_DATE),
    MONTHNAME(ORDER_DATE),
    QUARTER(ORDER_DATE),
    YEAR(ORDER_DATE)
FROM ECOMMERCE_DB.RAW.RAW_ECOM_SALES;

-- Fact Table: FACT_SALES
CREATE OR REPLACE TABLE FACT_SALES (
    SALES_KEY INTEGER IDENTITY(1,1) PRIMARY KEY,
    ORDER_SK INTEGER, -- FK to STAGING.ORDERS (if needed for drill-through to transactional detail)
    CUSTOMER_KEY INTEGER, -- FK to DIM_CUSTOMER
    PRODUCT_KEY INTEGER, -- FK to DIM_PRODUCT
    DATE_KEY INTEGER, -- FK to DIM_DATE
    QUANTITY INTEGER,
    UNIT_PRICE DECIMAL(10, 2),
    TOTAL_SALES_AMOUNT DECIMAL(10, 2)
);

-- Step 2: Populate Fact and Dimension Tables

-- Populate DIM_CUSTOMER
INSERT INTO DIM_CUSTOMER (CUSTOMER_KEY, CUSTOMER_ID, CUSTOMER_NAME, CUSTOMER_EMAIL, CUSTOMER_ADDRESS)
SELECT
    CUSTOMER_SK, -- Use the surrogate key from STAGING as the DW key
    CUSTOMER_ID,
    CUSTOMER_NAME,
    CUSTOMER_EMAIL,
    CUSTOMER_ADDRESS
FROM ECOMMERCE_DB.STAGING.CUSTOMERS;

-- Populate DIM_PRODUCT
INSERT INTO DIM_PRODUCT (PRODUCT_KEY, PRODUCT_ID, PRODUCT_NAME, PRODUCT_CATEGORY, PRODUCT_PRICE)
SELECT
    PRODUCT_SK, -- Use the surrogate key from STAGING as the DW key
    PRODUCT_ID,
    PRODUCT_NAME,
    PRODUCT_CATEGORY,
    PRODUCT_PRICE
FROM ECOMMERCE_DB.STAGING.PRODUCTS;

-- Populate FACT_SALES
INSERT INTO FACT_SALES (ORDER_SK, CUSTOMER_KEY, PRODUCT_KEY, DATE_KEY, QUANTITY, UNIT_PRICE, TOTAL_SALES_AMOUNT)
SELECT
    oi.ORDER_SK,
    c.CUSTOMER_KEY,
    p.PRODUCT_KEY,
    TO_NUMBER(TO_CHAR(o.ORDER_DATE, 'YYYYMMDD')), -- Get DATE_KEY from order date
    oi.QUANTITY,
    dp.PRODUCT_PRICE AS UNIT_PRICE, -- Get unit price from the dimension
    oi.QUANTITY * dp.PRODUCT_PRICE AS TOTAL_SALES_AMOUNT -- Calculate total sales amount
FROM ECOMMERCE_DB.STAGING.ORDER_ITEMS oi
JOIN ECOMMERCE_DB.STAGING.ORDERS o ON oi.ORDER_SK = o.ORDER_SK
JOIN ECOMMERCE_DB.STAGING.CUSTOMERS sc ON o.CUSTOMER_SK = sc.CUSTOMER_SK -- Join to staging customer to get customer_id
JOIN ECOMMERCE_DB.STAGING.PRODUCTS sp ON oi.PRODUCT_SK = sp.PRODUCT_SK -- Join to staging product to get product_id
JOIN DIM_CUSTOMER c ON sc.CUSTOMER_ID = c.CUSTOMER_ID -- Join to DW dimension
JOIN DIM_PRODUCT dp ON sp.PRODUCT_ID = dp.PRODUCT_ID; -- Join to DW dimension

-- Verify dimensional data
SELECT * FROM DIM_CUSTOMER LIMIT 5;
SELECT * FROM DIM_PRODUCT LIMIT 5;
SELECT * FROM DIM_DATE LIMIT 5;
SELECT * FROM FACT_SALES LIMIT 5;

-- Step 3: Explore Snowflake Schema (Conceptual)
-- A Snowflake schema would involve normalizing a dimension.
-- For example, if DIM_PRODUCT had a `CATEGORY_ID` and you created a separate `DIM_CATEGORY` table:
-- CREATE OR REPLACE TABLE DIM_CATEGORY (
--     CATEGORY_KEY INTEGER PRIMARY KEY,
--     CATEGORY_NAME VARCHAR(100)
-- );
-- Then DIM_PRODUCT would have a foreign key to DIM_CATEGORY_KEY.
-- This example keeps DIM_PRODUCT simple for clarity, but you can extend it.

----------------------------------------------------------------------------------------------------

-- Module 4: Data Warehouse Architecture & ELT

-- Step 1: ELT Process Demonstration (already done through the previous steps)
-- E: Extract - Data is 'extracted' from source (simulated by our RAW_ECOM_SALES table).
-- L: Load - Data is 'loaded' into Snowflake (RAW_ECOM_SALES is our landing zone).
-- T: Transform - Data is 'transformed' from RAW to STAGING (normalized) and then to ANALYTICS (dimensional).

-- Step 2: Run Analytical Queries

-- Total Sales by Product Category
SELECT
    dp.PRODUCT_CATEGORY,
    SUM(fs.TOTAL_SALES_AMOUNT) AS TOTAL_SALES
FROM FACT_SALES fs
JOIN DIM_PRODUCT dp ON fs.PRODUCT_KEY = dp.PRODUCT_KEY
GROUP BY dp.PRODUCT_CATEGORY
ORDER BY TOTAL_SALES DESC;

-- Total Sales by Customer
SELECT
    dc.CUSTOMER_NAME,
    SUM(fs.TOTAL_SALES_AMOUNT) AS TOTAL_SALES
FROM FACT_SALES fs
JOIN DIM_CUSTOMER dc ON fs.CUSTOMER_KEY = dc.CUSTOMER_KEY
GROUP BY dc.CUSTOMER_NAME
ORDER BY TOTAL_SALES DESC;

-- Daily Sales Trend
SELECT
    dd.FULL_DATE,
    SUM(fs.TOTAL_SALES_AMOUNT) AS DAILY_SALES
FROM FACT_SALES fs
JOIN DIM_DATE dd ON fs.DATE_KEY = dd.DATE_KEY
GROUP BY dd.FULL_DATE
ORDER BY dd.FULL_DATE ASC;

-- Top 3 Products by Quantity Sold
SELECT
    dp.PRODUCT_NAME,
    SUM(fs.QUANTITY) AS TOTAL_QUANTITY_SOLD
FROM FACT_SALES fs
JOIN DIM_PRODUCT dp ON fs.PRODUCT_KEY = dp.PRODUCT_KEY
GROUP BY dp.PRODUCT_NAME
ORDER BY TOTAL_QUANTITY_SOLD DESC
LIMIT 3;

-- Customers who bought more than one product
SELECT
    dc.CUSTOMER_NAME,
    COUNT(DISTINCT fs.PRODUCT_KEY) AS UNIQUE_PRODUCTS_BOUGHT
FROM FACT_SALES fs
JOIN DIM_CUSTOMER dc ON fs.CUSTOMER_KEY = dc.CUSTOMER_KEY
GROUP BY dc.CUSTOMER_NAME
HAVING UNIQUE_PRODUCTS_BOUGHT > 1
ORDER BY UNIQUE_PRODUCTS_BOUGHT DESC;

