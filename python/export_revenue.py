from pathlib import Path

import duckdb
import pandas as pd

# connexion à DuckDB
con = duckdb.connect("work/comptoir.duckdb")

# récupération du chiffre d'affaires par produit
ca_produit = con.execute("""
    SELECT *
    FROM revenue_product
""").df()

# récupération du chiffre d'affaires total
ca_total = con.execute("""
    SELECT *
    FROM revenue_total
""").df()

print("Nombre de produits :", len(ca_produit))
print(ca_produit.head())

print("Chiffre d'affaires total :")
print(ca_total)

Path("outputs").mkdir(exist_ok=True)

with pd.ExcelWriter("outputs/chiffre_affaires.xlsx", engine="openpyxl") as writer:
    ca_produit.to_excel(writer, sheet_name="CA_par_produit", index=False)

    ca_total.to_excel(writer, sheet_name="CA_total", index=False)

print("Fichier Excel créé : outputs/chiffre_affaires.xlsx")


con.close()
