-- Chiffre d'affaires par produit
CREATE OR REPLACE TABLE revenue_product AS
SELECT
    product_id,
    sku,
    post_title,
    CAST(price AS DECIMAL(10,2)) AS price,
    CAST(total_sales AS INTEGER) AS total_sales,
    CAST(price AS DECIMAL(10,2))
        * CAST(total_sales AS INTEGER) AS chiffre_affaires
FROM merged_data;


-- Chiffre d'affaires global
CREATE OR REPLACE TABLE revenue_total AS
SELECT
    SUM(chiffre_affaires) AS chiffre_affaires_total
FROM revenue_product;