Slowly Changing Dimensions (SCDs): A Practical Guide with Snowflake
Slowly Changing Dimensions (SCDs) are a fundamental concept in data warehousing. They refer to dimensions that have data that changes slowly over time, rather than on a regular, predictable schedule. For example, a customer's address, a product's price, or an employee's department are attributes that might change, and how we handle these changes is crucial for historical reporting and analysis.

There are several types of SCDs, each dictating a different method for handling changes to dimensional data. For this hands-on session, we will focus on the two most common types: SCD Type 1 and SCD Type 2.

What are We Trying to Solve?
Imagine you have a PRODUCTS dimension table in your data warehouse. This table stores information about the products your company sells, like PRODUCT_ID, PRODUCT_NAME, and PRICE.

What happens if the price of a product changes?

Do we update the existing product record with the new price, losing the old price information?

Or do we keep a history of all price changes for that product?

SCD methodologies provide strategies for managing these kinds of changes.

SCD Type 1: Overwriting the Old Value
Concept:
In SCD Type 1, when an attribute value changes, the old value in the dimension table is simply overwritten with the new value. No history of the attribute's previous values is kept.

Analogy: Think of it like updating your contact information in a single address book entry. The old address is erased and replaced by the new one.

Use Cases:

Correcting errors in data (e.g., fixing a typo in a product name).

When historical tracking of an attribute is not important for business analysis.

For attributes that change due to reclassification but don't represent a historical shift (e.g., minor re-categorization).

Pros:

Simple to implement.

Requires minimal storage space as no historical data is kept.

Cons:

Historical information is lost. You cannot analyze trends based on the attribute's past values.

If an old value was associated with historical facts (e.g., sales made at an old price), updating the dimension can make it appear as if those historical facts occurred with the new attribute value, which can be misleading.

Example:
If a product "SuperWidget" had its price changed from $19.99 to $21.99:

Before Change:
| PRODUCT_ID | PRODUCT_NAME | PRICE   |
|------------|--------------|---------|
| P101       | SuperWidget  | $19.99  |

After SCD Type 1 Update:
| PRODUCT_ID | PRODUCT_NAME | PRICE   |
|------------|--------------|---------|
| P101       | SuperWidget  | $21.99  |

The previous price of $19.99 is lost.

SCD Type 2: Adding a New Row for Changes (Preserving History)
Concept:
In SCD Type 2, when an attribute value changes, a new row is added to the dimension table to store the new value. The existing row, representing the previous state of the dimension, is preserved but marked as no longer current. This allows for full historical tracking.

Analogy: Think of it like keeping all your past rental agreements. Each time you move, you get a new agreement (a new row) with new dates, but you still have the old ones for reference.

Common Methods to Implement SCD Type 2:

Effective Date Ranges: Each row has a START_DATE and an END_DATE column. The current record has an END_DATE set to a future date (e.g., '9999-12-31') or NULL. When a change occurs, the END_DATE of the current record is updated to the date of the change, and a new record is inserted with the new attribute values, a START_DATE of the change date, and an END_DATE of '9999-12-31'.

Current Indicator Flag: A column (e.g., IS_CURRENT, CURRENT_FLAG) indicates whether the record is the most recent version (e.g., TRUE/FALSE, Y/N, 1/0). When a change occurs, the flag on the old record is set to 'FALSE', and a new record is inserted with the flag set to 'TRUE'. This is often used in conjunction with effective dates.

Version Number: Each version of the dimension member gets an incrementing version number.

Use Cases:

When historical analysis of dimensional attributes is critical (e.g., tracking customer address changes over time to analyze regional sales, or product price changes to understand margin impact).

Regulatory compliance requiring historical data retention.

Pros:

Complete history of changes is maintained.

Enables accurate historical reporting and trend analysis.

Cons:

More complex to implement than SCD Type 1.

Dimension table can grow significantly larger, potentially impacting query performance if not managed well (e.g., with proper indexing and partitioning).

Requires careful handling of surrogate keys for joining with fact tables. Fact tables typically join to the dimension using a surrogate key that is unique for each version of the dimension record.

Example:
If a product "SuperWidget" (PRODUCT_ID P101) had its price changed from $19.99 to $21.99 on 2024-06-01:

Before Change (assuming initial load on 2024-01-01):
| DIM_KEY | PRODUCT_ID | PRODUCT_NAME | PRICE  | EFFECTIVE_DATE | END_DATE   | IS_CURRENT |
|---------|------------|--------------|--------|----------------|------------|------------|
| 1       | P101       | SuperWidget  | $19.99 | 2024-01-01     | 9999-12-31 | TRUE       |

After SCD Type 2 Update (change on 2024-06-01):
| DIM_KEY | PRODUCT_ID | PRODUCT_NAME | PRICE  | EFFECTIVE_DATE | END_DATE   | IS_CURRENT |
|---------|------------|--------------|--------|----------------|------------|------------|
| 1       | P101       | SuperWidget  | $19.99 | 2024-01-01     | 2024-05-31 | FALSE      |
| 2       | P101       | SuperWidget  | $21.99 | 2024-06-01     | 9999-12-31 | TRUE       |

A new row (DIM_KEY 2) is added with the new price. The old row (DIM_KEY 1) is updated to reflect its historical status.

Snowflake Hands-On Demonstration
Let's set up the environment and walk through implementing SCD Type 1 and Type 2 in Snowflake.

Scenario: We have a source system that provides product information. We'll call this RAW_PRODUCTS. We want to load this data into our dimension tables, DIM_PRODUCTS_SCD1 and DIM_PRODUCTS_SCD2.

1. Setup: Create Database, Schema, and Source Table

First, let's create a database and schema if you don't have one already for this demo. Then, we'll create our raw source table.

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

Output of SELECT * FROM RAW_PRODUCTS (example):
| PRODUCT_ID | PRODUCT_NAME        | CATEGORY    | PRICE   | LAST_UPDATED_TIMESTAMP      |
|------------|---------------------|-------------|---------|-----------------------------|
| P001       | Laptop Pro 15       | Electronics | 1200.00 | 2024-06-02 15:30:00.123 ... |
| P002       | Wireless Mouse      | Accessories | 25.00   | 2024-06-02 15:30:00.123 ... |
| P003       | Office Chair Deluxe | Furniture   | 150.00  | 2024-06-02 15:30:00.123 ... |

2. SCD Type 1 Implementation in Snowflake
A. Create the SCD Type 1 Dimension Table

This table will store the current state of our products, overwriting attributes when they change. The PRODUCT_ID will be our natural key.

CREATE OR REPLACE TABLE DIM_PRODUCTS_SCD1 (
    PRODUCT_ID VARCHAR(10) PRIMARY KEY, -- Natural Key
    PRODUCT_NAME VARCHAR(100),
    CATEGORY VARCHAR(50),
    PRICE DECIMAL(10,2),
    DW_LAST_UPDATED_TIMESTAMP TIMESTAMP_NTZ -- Timestamp of last update in the DWH
);

B. Initial Load into DIM_PRODUCTS_SCD1

We'll load all records from RAW_PRODUCTS into our dimension table.

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

Output of SELECT * FROM DIM_PRODUCTS_SCD1 (example):
| PRODUCT_ID | PRODUCT_NAME        | CATEGORY    | PRICE   | DW_LAST_UPDATED_TIMESTAMP   |
|------------|---------------------|-------------|---------|-----------------------------|
| P001       | Laptop Pro 15       | Electronics | 1200.00 | 2024-06-02 15:31:00.456 ... |
| P002       | Wireless Mouse      | Accessories | 25.00   | 2024-06-02 15:31:00.456 ... |
| P003       | Office Chair Deluxe | Furniture   | 150.00  | 2024-06-02 15:31:00.456 ... |

C. Simulate Changes in the Source Data

Let's assume the price of 'Laptop Pro 15' (P001) changes, and a new product 'Gaming Keyboard' (P004) is introduced.

-- Simulate a price update for P001 and a name correction for P002
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

Output of SELECT * FROM RAW_PRODUCTS after changes (example):
| PRODUCT_ID | PRODUCT_NAME             | CATEGORY    | PRICE   | LAST_UPDATED_TIMESTAMP      |
|------------|--------------------------|-------------|---------|-----------------------------|
| P001       | Laptop Pro 15            | Electronics | 1250.00 | 2024-06-02 15:32:00.789 ... |
| P002       | Ergonomic Wireless Mouse | Accessories | 25.00   | 2024-06-02 15:32:00.789 ... |
| P003       | Office Chair Deluxe      | Furniture   | 150.00  | 2024-06-02 15:30:00.123 ... |
| P004       | Gaming Keyboard          | Accessories | 75.00   | 2024-06-02 15:32:00.789 ... |

D. Apply SCD Type 1 Logic using MERGE

The MERGE statement is perfect for SCD Type 1. It can update existing rows if they've changed or insert new rows if they don't exist in the dimension table.

MERGE INTO DIM_PRODUCTS_SCD1 AS target
USING (
    -- Select the latest version of each product from the raw source
    -- This subquery is important if your source could have multiple entries for the same PRODUCT_ID
    -- and you only want to process the most recent one.
    -- For this demo, RAW_PRODUCTS is assumed to have one record per PRODUCT_ID.
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

-- View the SCD1 dimension table after the MERGE
SELECT * FROM DIM_PRODUCTS_SCD1 ORDER BY PRODUCT_ID;

Expected Output of SELECT * FROM DIM_PRODUCTS_SCD1 after MERGE:
| PRODUCT_ID | PRODUCT_NAME             | CATEGORY    | PRICE   | DW_LAST_UPDATED_TIMESTAMP   |
|------------|--------------------------|-------------|---------|-----------------------------|
| P001       | Laptop Pro 15            | Electronics | 1250.00 | 2024-06-02 15:33:00.999 ... | | P002       | Ergonomic Wireless Mouse | Accessories | 25.00   | 2024-06-02 15:33:00.999 ... | | P003       | Office Chair Deluxe      | Furniture   | 150.00  | 2024-06-02 15:31:00.456 ... | | P004       | Gaming Keyboard          | Accessories | 75.00   | 2024-06-02 15:33:00.999 ... | Key Observation for SCD Type 1:

The price for P001 is now $1250.00. The old price of $1200.00 is gone.

The name for P002 is now 'Ergonomic Wireless Mouse'. The old name 'Wireless Mouse' is gone.

The new product P004 has been added.

3. SCD Type 2 Implementation in Snowflake
A. Create the SCD Type 2 Dimension Table

This table will store the history of changes. We'll add:

DIM_PRODUCT_KEY: A surrogate key to uniquely identify each version of a product record.

EFFECTIVE_DATE: The date from which this version of the product record is valid.

END_DATE: The date until which this version of the product record was valid.

IS_CURRENT_FLAG: A boolean/varchar to easily identify the current active record for a product.

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

Note: AUTOINCREMENT is a convenient way to generate surrogate keys in Snowflake.

B. Initial Load into DIM_PRODUCTS_SCD2

For the initial load, all records are current, with an EFFECTIVE_DATE of today (or a historical load date) and an END_DATE set far in the future (e.g., '9999-12-31').

-- Reset RAW_PRODUCTS to its initial state for a clean SCD2 demonstration
TRUNCATE TABLE RAW_PRODUCTS;
INSERT INTO RAW_PRODUCTS (PRODUCT_ID, PRODUCT_NAME, CATEGORY, PRICE, LAST_UPDATED_TIMESTAMP) VALUES
('P001', 'Laptop Pro 15', 'Electronics', 1200.00, '2024-01-01 10:00:00'), -- Assuming initial load date
('P002', 'Wireless Mouse', 'Accessories', 25.00, '2024-01-01 10:00:00'),
('P003', 'Office Chair Deluxe', 'Furniture', 150.00, '2024-01-01 10:00:00');

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

Output of SELECT * FROM DIM_PRODUCTS_SCD2 (example, DIM_PRODUCT_KEY may vary):
| DIM_PRODUCT_KEY | PRODUCT_ID | PRODUCT_NAME        | CATEGORY    | PRICE   | EFFECTIVE_DATE | END_DATE   | IS_CURRENT_FLAG | DW_LOAD_TIMESTAMP           |
|-----------------|------------|---------------------|-------------|---------|----------------|------------|-----------------|-----------------------------|
| 1               | P001       | Laptop Pro 15       | Electronics | 1200.00 | 2024-01-01     | 9999-12-31 | TRUE            | 2024-06-02 15:35:00.111 ... |
| 2               | P002       | Wireless Mouse      | Accessories | 25.00   | 2024-01-01     | 9999-12-31 | TRUE            | 2024-06-02 15:35:00.111 ... |
| 3               | P003       | Office Chair Deluxe | Furniture   | 150.00  | 2024-01-01     | 9999-12-31 | TRUE            | 2024-06-02 15:35:00.111 ... |

C. Simulate Changes in the Source Data (for SCD Type 2)

Let's simulate changes that will require historical tracking.

Price of 'Laptop Pro 15' (P001) changes from $1200.00 to $1250.00 on '2024-03-15'.

Category of 'Wireless Mouse' (P002) changes from 'Accessories' to 'Computer Peripherals' on '2024-04-01'.

A new product 'Gaming Keyboard' (P004) is introduced on '2024-05-01'.

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

D. Apply SCD Type 2 Logic using MERGE (or Staged Approach)

Implementing SCD Type 2 with a single MERGE statement can be complex because you need to perform two actions for existing, changed records: update the old record (expire it) and insert a new record (the current version). A common approach involves:

Identifying changes.

Inserting new versions for changed records.

Updating old versions of changed records (expiring them).

Inserting brand new records.

Snowflake's MERGE can handle this, but it requires careful structuring. We'll use a MERGE statement that leverages a subquery to identify changes and new records.

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

Expected Output of SELECT * FROM DIM_PRODUCTS_SCD2 after SCD2 logic:
(DIM_PRODUCT_KEY values are illustrative and will be sequential based on insertion order)

DIM_PRODUCT_KEY

PRODUCT_ID

PRODUCT_NAME

CATEGORY

PRICE

EFFECTIVE_DATE

END_DATE

IS_CURRENT_FLAG

DW_LOAD_TIMESTAMP

1

P001

Laptop Pro 15

Electronics

1200.00

2024-01-01

2024-03-14

FALSE

2024-06-02 15:40:00.xxx ...

P001 (Laptop Pro 15):

The original record (DIM_PRODUCT_KEY 1) now has END_DATE = '2024-03-14' and IS_CURRENT_FLAG = FALSE.

A new record (DIM_PRODUCT_KEY 4) is added with the new price $1250.00, EFFECTIVE_DATE = '2024-03-15', END_DATE = '9999-12-31', and IS_CURRENT_FLAG = TRUE.

P002 (Wireless Mouse):

The original record (DIM_PRODUCT_KEY 2) now has END_DATE = '2024-03-31' and IS_CURRENT_FLAG = FALSE.

A new record (DIM_PRODUCT_KEY 5) is added with the new category 'Computer Peripherals', EFFECTIVE_DATE = '2024-04-01', and IS_CURRENT_FLAG = TRUE.

P003 (Office Chair Deluxe):

This product had no changes in the RAW_PRODUCTS batch that indicated a modification to its attributes (price, name, category). Therefore, its original record (DIM_PRODUCT_KEY 3) remains unchanged and current.

P004 (Gaming Keyboard):

This is a new product, so a new record (DIM_PRODUCT_KEY 6) is inserted with EFFECTIVE_DATE = '2024-05-01' and IS_CURRENT_FLAG = TRUE.

This demonstrates how SCD Type 2 preserves the complete history of changes to the product dimension.

Alternative SCD Type 2 MERGE (More Complex Single Statement)
It is possible to write a more complex single MERGE statement that handles both inserts and the logic for expiring old records and inserting new ones for changes. This often involves using the WHEN MATCHED clause multiple times with different conditions or more intricate subqueries. However, the two-step approach (Insert new/changed, then Update old) is often clearer and easier to debug.

Here's a conceptual example of how one might approach a more combined MERGE, though it can get quite involved:

-- THIS IS A CONCEPTUAL, MORE ADVANCED MERGE AND MAY NEED ADJUSTMENT
-- It attempts to do more in one go, but can be harder to read.
-- The previous two-step approach is often preferred for clarity.

/*
MERGE INTO DIM_PRODUCTS_SCD2 d
USING (
    SELECT
        r.PRODUCT_ID,
        r.PRODUCT_NAME,
        r.CATEGORY,
        r.PRICE,
        DATE(r.LAST_UPDATED_TIMESTAMP) AS SOURCE_EFFECTIVE_DATE,
        -- Determine if this is a new product, or an existing one with changes
        curr.DIM_PRODUCT_KEY AS CURRENT_DIM_KEY,
        curr.PRODUCT_NAME AS CURRENT_PRODUCT_NAME,
        curr.CATEGORY AS CURRENT_CATEGORY,
        curr.PRICE AS CURRENT_PRICE,
        CASE
            WHEN curr.DIM_PRODUCT_KEY IS NULL THEN 'INSERT_NEW' -- New product
            WHEN (r.PRODUCT_NAME <> curr.PRODUCT_NAME OR r.CATEGORY <> curr.CATEGORY OR r.PRICE <> curr.PRICE) THEN 'UPDATE_EXISTING' -- Existing product with changes
            ELSE 'NO_CHANGE'
        END AS ACTION_TYPE
    FROM RAW_PRODUCTS r
    LEFT JOIN DIM_PRODUCTS_SCD2 curr
      ON r.PRODUCT_ID = curr.PRODUCT_ID AND curr.IS_CURRENT_FLAG = TRUE
) AS src
ON d.DIM_PRODUCT_KEY = src.CURRENT_DIM_KEY AND src.ACTION_TYPE = 'UPDATE_EXISTING' AND d.IS_CURRENT_FLAG = TRUE

-- Clause to expire the old current record if there's a change
WHEN MATCHED AND src.ACTION_TYPE = 'UPDATE_EXISTING' THEN
    UPDATE SET
        d.END_DATE = src.SOURCE_EFFECTIVE_DATE - INTERVAL '1 DAY',
        d.IS_CURRENT_FLAG = FALSE,
        d.DW_LOAD_TIMESTAMP = CURRENT_TIMESTAMP()

-- Clause to insert the new version of an existing changed record OR a brand new record
-- This part is tricky because MERGE typically expects one target row per source row for inserts.
-- To handle both expiring an old row AND inserting a new one for the *same source change*,
-- you often need to UNION source data or use multiple MERGE/INSERT/UPDATE statements.
-- The Snowflake MERGE statement can insert if NOT MATCHED on the primary join condition.
-- For SCD2, the "new" version is effectively a new row, not a direct match for an insert.

-- A common pattern is to handle inserts of new versions and brand-new products separately
-- from the update that expires old records, as shown in the two-step method above.
-- A single MERGE for full SCD2 (expire + insert new version) is complex because the "insert new version"
-- doesn't directly match an existing row in a way that MERGE's WHEN NOT MATCHED clause easily handles
-- in the same operation as expiring the old one based on a MATCHED condition.

-- Therefore, the prior two-step (or multi-step) approach is generally more robust and understandable.
-- If you were to try to force it into one MERGE, you might use a source that generates two rows
-- for each change (one to match and update, one to not match and insert), which adds complexity.
*/

The above commented-out section highlights why the multi-step approach is often preferred for SCD Type 2 in SQL.

Conclusion and Choosing the Right Type
SCD Type 1 (Overwrite): Use when historical data for an attribute is not needed. Simple, but loses history.

SCD Type 2 (Add Row): Use when historical tracking is essential for analysis and reporting. More complex but provides a complete audit trail.

Other SCD Types (Brief Mention):

SCD Type 0 (Retain Original): Attributes are fixed and never change.

SCD Type 3 (Add New Attribute): Store a limited amount of history by adding a new column for the "previous" value. For example, CURRENT_PRICE and PREVIOUS_PRICE. This is less common for extensive history.

SCD Type 4 (History Table): Use a separate history table to track all changes, while the main dimension table holds only current values.

SCD Type 6 (Hybrid): Combines elements of Type 1, 2, and 3. For example, overwriting a minor attribute (Type 1) while tracking history for major attributes (Type 2) and perhaps having a "current" flag.

The choice of SCD type depends entirely on your business requirements for historical data retention and analysis. Snowflake's powerful SQL capabilities, including the MERGE statement and window functions, provide flexible tools for implementing these strategies.

Remember to consider the impact on storage and query performance, especially with SCD Type 2, and design your dimension tables and ETL processes accordingly.
