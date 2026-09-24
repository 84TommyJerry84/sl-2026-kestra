CREATE OR REPLACE TABLE merged_data AS
SELECT
    e.product_id,
    e.onsale_web,
    e.price,
    e.stock_quantity,
    e.stock_status,
    l.id_web,
    w.sku,
    w.post_type,
    w.post_title,
    w.total_sales
FROM erp_dedup AS e
INNER JOIN liaison_dedup AS l
    ON e.product_id = l.product_id
INNER JOIN web_dedup AS w
    ON l.id_web = w.sku;