-- =============================================================
-- NLQ Demo Database — Seed Data
-- Schema: ecommerce (5 tables, ~100 rows, realistic joins)
-- =============================================================

-- ── Regions ──
CREATE TABLE IF NOT EXISTS regions (
    region_id   SERIAL PRIMARY KEY,
    region_name VARCHAR(50)  NOT NULL,
    country     VARCHAR(100) NOT NULL,
    timezone    VARCHAR(50)
);

INSERT INTO regions (region_name, country, timezone) VALUES
('North America', 'United States', 'America/New_York'),
('North America', 'Canada',        'America/Toronto'),
('EMEA',          'United Kingdom', 'Europe/London'),
('EMEA',          'Germany',        'Europe/Berlin'),
('APAC',          'Japan',          'Asia/Tokyo'),
('APAC',          'Australia',      'Australia/Sydney'),
('LATAM',         'Brazil',         'America/Sao_Paulo'),
('LATAM',         'Mexico',         'America/Mexico_City');

-- ── Customers ──
CREATE TABLE IF NOT EXISTS customers (
    customer_id    SERIAL PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    email          VARCHAR(150),
    signup_date    DATE NOT NULL,
    segment        VARCHAR(30) NOT NULL,
    lifetime_value NUMERIC(12,2) DEFAULT 0,
    region_id      INT REFERENCES regions(region_id),
    is_active      BOOLEAN DEFAULT TRUE
);

INSERT INTO customers (name, email, signup_date, segment, lifetime_value, region_id, is_active) VALUES
('Alice Johnson',   'alice@example.com',   '2022-01-15', 'enterprise',  45200.00, 1, TRUE),
('Bob Smith',       'bob@example.com',     '2022-03-22', 'mid_market',  18900.00, 1, TRUE),
('Carlos Rivera',   'carlos@example.com',  '2022-06-10', 'smb',          5400.00, 7, TRUE),
('Diana Chen',      'diana@example.com',   '2022-08-01', 'enterprise',  62100.00, 5, TRUE),
('Eva Mueller',     'eva@example.com',     '2023-01-05', 'individual',   1200.00, 4, TRUE),
('Frank Wilson',    'frank@example.com',   '2023-02-18', 'mid_market',  22300.00, 3, TRUE),
('Grace Kim',       'grace@example.com',   '2023-04-30', 'enterprise',  38700.00, 5, TRUE),
('Hassan Ali',      'hassan@example.com',  '2023-06-12', 'smb',          7800.00, 4, FALSE),
('Isla Torres',     'isla@example.com',    '2023-09-01', 'individual',   2100.00, 8, TRUE),
('Jake Brown',      'jake@example.com',    '2023-11-20', 'mid_market',  15600.00, 2, TRUE),
('Keiko Tanaka',    'keiko@example.com',   '2024-01-10', 'enterprise',  28400.00, 5, TRUE),
('Liam OConnor',    'liam@example.com',    '2024-02-14', 'smb',          4300.00, 3, TRUE);

-- ── Products ──
CREATE TABLE IF NOT EXISTS products (
    product_id    SERIAL PRIMARY KEY,
    product_name  VARCHAR(150) NOT NULL,
    category      VARCHAR(50)  NOT NULL,
    subcategory   VARCHAR(50),
    brand         VARCHAR(80),
    current_price NUMERIC(10,2) NOT NULL,
    cost_price    NUMERIC(10,2),
    is_active     BOOLEAN DEFAULT TRUE,
    launch_date   DATE
);

INSERT INTO products (product_name, category, subcategory, brand, current_price, cost_price, is_active, launch_date) VALUES
('Ultra Laptop Pro',     'electronics', 'laptops',      'TechBrand',   1299.99,  850.00, TRUE,  '2023-01-15'),
('Wireless Mouse X',     'electronics', 'peripherals',  'TechBrand',     49.99,   18.00, TRUE,  '2023-03-01'),
('Ergonomic Keyboard',   'electronics', 'peripherals',  'TypeMaster',    89.99,   35.00, TRUE,  '2023-04-10'),
('Premium Headphones',   'electronics', 'audio',        'SoundWave',    199.99,   80.00, TRUE,  '2023-06-20'),
('Cotton T-Shirt Basic', 'clothing',    'tops',         'BasicWear',     24.99,    8.00, TRUE,  '2023-02-01'),
('Running Shoes Pro',    'sports',      'footwear',     'SpeedFit',     129.99,   55.00, TRUE,  '2023-05-15'),
('Yoga Mat Premium',     'sports',      'equipment',    'FlexGear',      39.99,   12.00, TRUE,  '2023-07-01'),
('Organic Coffee Beans', 'food',        'beverages',    'BeanCo',        18.99,    7.00, TRUE,  '2023-08-10'),
('Smart Watch Elite',    'electronics', 'wearables',    'TechBrand',    349.99,  150.00, TRUE,  '2024-01-05'),
('Desk Lamp LED',        'home',        'lighting',     'BrightHome',    59.99,   22.00, TRUE,  '2023-09-15');

-- ── Orders ──
CREATE TABLE IF NOT EXISTS orders (
    order_id        SERIAL PRIMARY KEY,
    customer_id     INT REFERENCES customers(customer_id),
    order_date      DATE NOT NULL,
    status          VARCHAR(20) NOT NULL,
    total_amount    NUMERIC(12,2) NOT NULL,
    discount_amount NUMERIC(10,2) DEFAULT 0,
    shipping_cost   NUMERIC(10,2) DEFAULT 0,
    payment_method  VARCHAR(30),
    channel         VARCHAR(20),
    region_id       INT REFERENCES regions(region_id),
    created_at      TIMESTAMP DEFAULT NOW()
);

INSERT INTO orders (customer_id, order_date, status, total_amount, discount_amount, shipping_cost, payment_method, channel, region_id) VALUES
-- Q1 2024
( 1, '2024-01-05', 'completed',  1349.98, 0.00,  9.99, 'credit_card',    'web',        1),
( 2, '2024-01-12', 'completed',   139.98, 5.00,  4.99, 'paypal',         'mobile_app', 1),
( 4, '2024-01-20', 'completed',  1499.98, 0.00, 12.99, 'credit_card',    'web',        5),
( 6, '2024-02-01', 'completed',   289.98, 0.00,  7.99, 'bank_transfer',  'web',        3),
( 7, '2024-02-10', 'completed',   399.98, 20.00, 0.00, 'credit_card',    'in_store',   5),
( 3, '2024-02-15', 'completed',    63.98, 0.00,  4.99, 'paypal',         'mobile_app', 7),
(10, '2024-03-01', 'completed',   179.98, 0.00,  6.99, 'credit_card',    'web',        2),
(11, '2024-03-08', 'completed',  1649.98, 50.00, 0.00, 'credit_card',    'web',        5),
( 5, '2024-03-15', 'cancelled',    24.99, 0.00,  4.99, 'paypal',         'mobile_app', 4),
( 1, '2024-03-20', 'completed',   249.98, 10.00, 0.00, 'credit_card',    'in_store',   1),
-- Q2 2024
( 2, '2024-04-02', 'completed',    89.99, 0.00,  4.99, 'paypal',         'web',        1),
( 4, '2024-04-15', 'completed',   349.99, 0.00,  9.99, 'credit_card',    'mobile_app', 5),
( 8, '2024-04-20', 'refunded',    199.99, 0.00,  7.99, 'credit_card',    'web',        4),
( 9, '2024-05-01', 'completed',    57.98, 0.00,  4.99, 'bank_transfer',  'mobile_app', 8),
( 6, '2024-05-10', 'completed',  1299.99, 0.00,  0.00, 'credit_card',    'in_store',   3),
(12, '2024-05-18', 'completed',   169.98, 0.00,  6.99, 'paypal',         'web',        3),
( 3, '2024-06-01', 'completed',   129.99, 5.00,  4.99, 'credit_card',    'mobile_app', 7),
( 7, '2024-06-15', 'completed',    59.99, 0.00,  0.00, 'credit_card',    'in_store',   5),
-- Q3 2024
( 1, '2024-07-05', 'completed',   439.98, 0.00,  9.99, 'credit_card',    'web',        1),
(11, '2024-07-20', 'completed',    89.99, 0.00,  4.99, 'paypal',         'web',        5),
( 5, '2024-08-10', 'completed',    49.99, 0.00,  4.99, 'paypal',         'mobile_app', 4),
(10, '2024-08-25', 'completed',   219.98, 0.00,  6.99, 'credit_card',    'web',        2),
( 4, '2024-09-05', 'completed',    18.99, 0.00,  4.99, 'bank_transfer',  'mobile_app', 5),
(12, '2024-09-15', 'completed',    39.99, 0.00,  4.99, 'paypal',         'web',        3);

-- ── Order Items ──
CREATE TABLE IF NOT EXISTS order_items (
    item_id      SERIAL PRIMARY KEY,
    order_id     INT REFERENCES orders(order_id),
    product_id   INT REFERENCES products(product_id),
    quantity     INT NOT NULL,
    unit_price   NUMERIC(10,2) NOT NULL,
    line_total   NUMERIC(12,2) NOT NULL,
    discount_pct NUMERIC(5,2) DEFAULT 0
);

INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total, discount_pct) VALUES
-- Order 1: Ultra Laptop + Wireless Mouse
(1,  1, 1, 1299.99, 1299.99, 0),
(1,  2, 1,   49.99,   49.99, 0),
-- Order 2: Keyboard + Mouse
(2,  3, 1,   89.99,   89.99, 0),
(2,  2, 1,   49.99,   49.99, 0),
-- Order 3: Laptop + Headphones
(3,  1, 1, 1299.99, 1299.99, 0),
(3,  4, 1,  199.99,  199.99, 0),
-- Order 4: Headphones + Keyboard
(4,  4, 1,  199.99,  199.99, 0),
(4,  3, 1,   89.99,   89.99, 0),
-- Order 5: Smart Watch + Headphones
(5,  9, 1,  349.99,  349.99, 0),
(5,  4, 1,  199.99,  179.99, 10),
-- Order 6: T-Shirt + Yoga Mat
(6,  5, 1,   24.99,   24.99, 0),
(6,  7, 1,   39.99,   38.99, 0),
-- Order 7: Running Shoes + Mouse
(7,  6, 1,  129.99,  129.99, 0),
(7,  2, 1,   49.99,   49.99, 0),
-- Order 8: Laptop + Smart Watch
(8,  1, 1, 1299.99, 1299.99, 0),
(8,  9, 1,  349.99,  349.99, 0),
-- Order 9: T-Shirt (cancelled)
(9,  5, 1,   24.99,   24.99, 0),
-- Order 10: Headphones + Desk Lamp
(10, 4, 1,  199.99,  189.99, 5),
(10, 10,1,   59.99,   59.99, 0),
-- Orders 11-24 (1 item each for simplicity)
(11, 3, 1,   89.99,   89.99, 0),
(12, 9, 1,  349.99,  349.99, 0),
(13, 4, 1,  199.99,  199.99, 0),
(14, 8, 2,   18.99,   37.98, 0),
(14, 5, 1,   24.99,   19.99, 20),
(15, 1, 1, 1299.99, 1299.99, 0),
(16, 6, 1,  129.99,  129.99, 0),
(16, 7, 1,   39.99,   39.99, 0),
(17, 6, 1,  129.99,  124.99, 4),
(18, 10,1,   59.99,   59.99, 0),
(19, 9, 1,  349.99,  349.99, 0),
(19, 3, 1,   89.99,   89.99, 0),
(20, 3, 1,   89.99,   89.99, 0),
(21, 2, 1,   49.99,   49.99, 0),
(22, 4, 1,  199.99,  199.99, 0),
(22, 5, 1,   24.99,   19.99, 20),
(23, 8, 1,   18.99,   18.99, 0),
(24, 7, 1,   39.99,   39.99, 0);
