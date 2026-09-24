INSTALL excel;
LOAD excel;

-- ERP : colonnes nécessaires au pipeline
CREATE OR REPLACE TABLE erp_clean AS
SELECT
    product_id,
    onsale_web,
    price,
    stock_quantity,
    stock_status
FROM read_xlsx(
    'data/Fichier_erp.xlsx',
    all_varchar = true
);

-- Liaison : correspondance entre l'identifiant ERP et l'identifiant Web
CREATE OR REPLACE TABLE liaison_clean AS
SELECT
    product_id,
    id_web
FROM read_xlsx(
    'data/fichier_liaison.xlsx',
    all_varchar = true
);

-- Web : seules les colonnes utilisées dans la suite du pipeline sont conservées
CREATE OR REPLACE TABLE web_clean AS
SELECT
    sku,
    post_type,
    post_title,
    total_sales
FROM read_xlsx(
    'data/Fichier_web.xlsx',
    all_varchar = true
)
WHERE sku IS NOT NULL
  AND TRIM(sku) <> '';