CREATE OR REPLACE TABLE merged_data AS
SELECT
    e.*,
    l.id_web,
    w.*
FROM erp_dedup AS e
INNER JOIN liaison_dedup AS l
    ON e.product_id = l.product_id
INNER JOIN web_dedup AS w
    ON l.id_web = w.sku;