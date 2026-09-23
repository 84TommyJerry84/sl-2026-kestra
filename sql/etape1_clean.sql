INSTALL excel;
LOAD excel;

CREATE OR REPLACE TABLE erp_clean AS
SELECT *
FROM read_xlsx(
    'data/Fichier_erp.xlsx',
    all_varchar = true
);

CREATE OR REPLACE TABLE liaison_clean AS
SELECT *
FROM read_xlsx(
    'data/fichier_liaison.xlsx',
    all_varchar = true
);

CREATE OR REPLACE TABLE web_clean AS
SELECT *
FROM read_xlsx(
    'data/Fichier_web.xlsx',
    all_varchar = true
)
WHERE sku IS NOT NULL
  AND TRIM(sku) <> '';