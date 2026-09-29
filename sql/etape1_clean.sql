CREATE OR REPLACE TABLE erp_clean AS
SELECT
    NULLIF(TRIM(product_id), '') AS product_id,
    NULLIF(TRIM(onsale_web), '') AS onsale_web,
    NULLIF(TRIM(price), '') AS price,
    NULLIF(TRIM(stock_quantity), '') AS stock_quantity,
    NULLIF(TRIM(stock_status), '') AS stock_status
FROM read_csv_auto(
    'prepared/erp.csv',
    header = true,
    all_varchar = true
);


CREATE OR REPLACE TABLE liaison_clean AS
SELECT
    NULLIF(TRIM(product_id), '') AS product_id,
    NULLIF(TRIM(id_web), '') AS id_web
FROM read_csv_auto(
    'prepared/liaison.csv',
    header = true,
    all_varchar = true
);


CREATE OR REPLACE TABLE web_clean AS
SELECT
    NULLIF(TRIM(sku), '') AS sku,
    NULLIF(TRIM(post_type), '') AS post_type,
    NULLIF(TRIM(post_title), '') AS post_title,
    NULLIF(TRIM(total_sales), '') AS total_sales
FROM read_csv_auto(
    'prepared/web.csv',
    header = true,
    all_varchar = true
)
WHERE sku IS NOT NULL
  AND TRIM(sku) <> '';