-- ERP : une seule ligne par product_id
CREATE OR REPLACE TABLE erp_dedup AS
SELECT
    product_id,
    onsale_web,
    price,
    stock_quantity,
    stock_status
FROM erp_clean
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY product_id
    ORDER BY product_id
) = 1;

-- LIAISON : une seule ligne par product_id
CREATE OR REPLACE TABLE liaison_dedup AS
SELECT
    product_id,
    id_web
FROM liaison_clean
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY product_id
    ORDER BY product_id
) = 1;

-- WEB : on conserve uniquement les produits
-- puis une seule ligne par sku
CREATE OR REPLACE TABLE web_dedup AS
SELECT
    sku,
    post_type,
    post_title,
    total_sales
FROM web_clean
WHERE post_type = 'product'
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY sku
    ORDER BY sku
) = 1;