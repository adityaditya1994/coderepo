CREATE DATABASE IF NOT EXISTS SCD_DEMO_DB;
USE DATABASE SCD_DEMO_DB;
-- Create a schema (if it doesn't exist)
CREATE SCHEMA IF NOT EXISTS DEMO_SCHEMA;

-- Use the database and schema

USE SCHEMA DEMO_SCHEMA;



CREATE OR REPLACE TABLE DIM_PRODUCTS_SCD2 (
    DIM_PRODUCT_KEY NUMBER(38,0) AUTOINCREMENT START 1 INCREMENT 1, -- Surrogate Key
    PRODUCT_ID VARCHAR(10),               -- Natural Key
    PRODUCT_NAME VARCHAR(100),
    CATEGORY VARCHAR(50),
    PRICE DECIMAL(10,2),
    EFFECTIVE_DATE DATE,
    END_DATE DATE,
    IS_CURRENT_FLAG BOOLEAN, -- TRUE for current, FALSE for historical
    DW_LOAD_TIMESTAMP TIMESTAMP_NTZ -- Timestamp of when the record was loaded/updated in DWH
);


-- Reset RAW_PRODUCTS to its initial state for a clean SCD2 demonstration
TRUNCATE TABLE RAW_PRODUCTS;
INSERT INTO RAW_PRODUCTS (PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE, LAST_UPDATED_TIMESTAMP) VALUES
('P001', 'Laptop Pro 15', 'Electronics', 1200.00, '2024-01-01 10:00:00'), -- Assuming initial load date
('P002', 'Wireless Mouse', 'Accessories', 25.00, '2024-01-01 10:00:00'),
('P003', 'Office Chair Deluxe', 'Furniture', 150.00, '2024-01-01 10:00:00');

select * from RAW_PRODUCTS ;

select * from DIM_PRODUCTS_SCD2 ;

-- Initial load for SCD Type 2
INSERT INTO DIM_PRODUCTS_SCD2 (
    PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE,
    EFFECTIVE_DATE, END_DATE, IS_CURRENT_FLAG, DW_LOAD_TIMESTAMP
)
SELECT
    rp.PRODUCT_ID,
    rp.PRODUCT_NAME,
    rp.CATEGORY,
    rp.PRICE,
    DATE(rp.LAST_UPDATED_TIMESTAMP), -- Effective from the source update timestamp (or a fixed load date)
    '9999-12-31',                   -- Standard high date for current records
    TRUE,                           -- This is the current version
    CURRENT_TIMESTAMP()             -- DWH load timestamp
FROM RAW_PRODUCTS rp;

-- View the SCD2 dimension table after initial load
SELECT * FROM DIM_PRODUCTS_SCD2 ORDER BY PRODUCT_ID, EFFECTIVE_DATE;



-- For SCD2, we typically process changes based on a "batch" of updates from the source.
-- Let's clear RAW_PRODUCTS and insert new "incoming" data representing these changes.
-- In a real ETL, this would be the data staged for the current ETL run.

TRUNCATE TABLE RAW_PRODUCTS;

-- Changed data for P001 (Price Update)
INSERT INTO RAW_PRODUCTS (PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE, LAST_UPDATED_TIMESTAMP) VALUES
('P001', 'Laptop Pro 15', 'Electronics', 1250.00, '2024-03-15 11:00:00');

-- Changed data for P002 (Category Update)
INSERT INTO RAW_PRODUCTS (PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE, LAST_UPDATED_TIMESTAMP) VALUES
('P002', 'Wireless Mouse', 'Computer Peripherals', 25.00, '2024-04-01 09:30:00');

-- Unchanged data for P003 (to ensure it's handled correctly - no new version should be created)
INSERT INTO RAW_PRODUCTS (PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE, LAST_UPDATED_TIMESTAMP) VALUES
('P003', 'Office Chair Deluxe', 'Furniture', 150.00, '2024-01-01 10:00:00'); -- Original timestamp, no actual change

-- New product P004
INSERT INTO RAW_PRODUCTS (PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE, LAST_UPDATED_TIMESTAMP) VALUES
('P004', 'Gaming Keyboard', 'Accessories', 75.00, '2024-05-01 14:00:00');

-- View the "new batch" of raw data
SELECT * FROM RAW_PRODUCTS ORDER BY PRODUCT_ID;


-- Staging table for changes (optional but good practice for complex logic)
CREATE OR REPLACE TEMPORARY TABLE STG_PRODUCT_CHANGES AS
SELECT
    s.PRODUCT_ID,
    s.PRODUCT_NAME,
    s.CATEGORY,
    s.PRICE,
    DATE(s.LAST_UPDATED_TIMESTAMP) AS SOURCE_EFFECTIVE_DATE, -- The date the change became effective in source
    d.DIM_PRODUCT_KEY AS EXISTING_DIM_KEY,
    d.PRODUCT_NAME AS OLD_PRODUCT_NAME,
    d.CATEGORY AS OLD_CATEGORY,
    d.PRICE AS OLD_PRICE,
    d.IS_CURRENT_FLAG AS OLD_IS_CURRENT
FROM RAW_PRODUCTS s
LEFT JOIN DIM_PRODUCTS_SCD2 d
    ON s.PRODUCT_ID = d.PRODUCT_ID AND d.IS_CURRENT_FLAG = TRUE -- Join only with the current active record in dimension
;

-- View staged changes
SELECT * FROM STG_PRODUCT_CHANGES;

-- Now, apply the SCD Type 2 logic using MERGE
-- This MERGE will handle:
-- 1. Inserts for completely new products.
-- 2. For existing products:
--    a. If attributes changed: It will effectively "insert" a new version.
--       The actual update of the old record to mark it non-current happens in a separate UPDATE statement.
--       Alternatively, a more complex MERGE could do this, or a stored procedure.
--       For clarity, we'll do a separate UPDATE for expiring old records.

-- Step 1: Insert new records for new products AND new versions for changed products
INSERT INTO DIM_PRODUCTS_SCD2 (
    PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE,
    EFFECTIVE_DATE, END_DATE, IS_CURRENT_FLAG, DW_LOAD_TIMESTAMP
)
SELECT
    sc.PRODUCT_ID,
    sc.PRODUCT_NAME,
    sc.CATEGORY,
    sc.PRICE,
    sc.SOURCE_EFFECTIVE_DATE,       -- Effective from the source change date
    '9999-12-31',                   -- Standard high date for current records
    TRUE,                           -- This is the new current version
    CURRENT_TIMESTAMP()             -- DWH load timestamp
FROM STG_PRODUCT_CHANGES sc
WHERE sc.EXISTING_DIM_KEY IS NULL -- It's a brand new product
   OR (                     -- It's an existing product, but attributes have changed
        sc.PRODUCT_NAME <> sc.OLD_PRODUCT_NAME OR
        sc.CATEGORY <> sc.OLD_CATEGORY OR
        sc.PRICE <> sc.OLD_PRICE
      );

-- Step 2: Expire old records for products that have a new version inserted in Step 1
UPDATE DIM_PRODUCTS_SCD2 target
SET
    target.END_DATE = new_versions.EFFECTIVE_DATE - INTERVAL '1 DAY', -- End date is day before new version starts
    target.IS_CURRENT_FLAG = FALSE,
    target.DW_LOAD_TIMESTAMP = CURRENT_TIMESTAMP()
FROM (
    -- Find products that had changes and thus got a new current record
    SELECT
        sc.PRODUCT_ID,
        sc.SOURCE_EFFECTIVE_DATE AS EFFECTIVE_DATE -- This is the effective date of the NEW record
    FROM STG_PRODUCT_CHANGES sc
    WHERE sc.EXISTING_DIM_KEY IS NOT NULL -- It was an existing product
      AND (                     -- And attributes have changed
        sc.PRODUCT_NAME <> sc.OLD_PRODUCT_NAME OR
        sc.CATEGORY <> sc.OLD_CATEGORY OR
        sc.PRICE <> sc.OLD_PRICE
      )
) AS new_versions
WHERE target.PRODUCT_ID = new_versions.PRODUCT_ID
  AND target.IS_CURRENT_FLAG = TRUE -- Only update the record that WAS current
  AND target.EFFECTIVE_DATE < new_versions.EFFECTIVE_DATE; -- Ensure we are not updating the newly inserted record

-- View the SCD2 dimension table after the updates
SELECT * FROM DIM_PRODUCTS_SCD2 ORDER BY PRODUCT_ID, EFFECTIVE_DATE;
