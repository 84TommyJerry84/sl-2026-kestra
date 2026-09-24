from pathlib import Path

import duckdb
import pandas as pd


DB_PATH = "work/comptoir.duckdb"
OUTPUT_DIR = Path("outputs")
OUTPUT_FILE = OUTPUT_DIR / "chiffre_affaires.xlsx"


def charger_chiffre_affaires(con):
    """Charge le chiffre d'affaires par produit et le chiffre d'affaires total."""
    ca_produit = con.execute(
        """
        SELECT
            product_id,
            sku,
            post_title,
            price,
            total_sales,
            chiffre_affaires
        FROM revenue_product
        """
    ).df()

    ca_total = con.execute(
        """
        SELECT
            chiffre_affaires_total
        FROM revenue_total
        """
    ).df()

    return ca_produit, ca_total


def exporter_excel(ca_produit, ca_total):
    """Exporte les résultats du chiffre d'affaires dans un fichier Excel."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl",
    ) as writer:
        ca_produit.to_excel(
            writer,
            sheet_name="CA_par_produit",
            index=False,
        )

        ca_total.to_excel(
            writer,
            sheet_name="CA_total",
            index=False,
        )


def main():
    con = duckdb.connect(DB_PATH)

    try:
        ca_produit, ca_total = charger_chiffre_affaires(con)

        print("Nombre de produits :", len(ca_produit))
        print(ca_produit.head())

        print("Chiffre d'affaires total :")
        print(ca_total)

        exporter_excel(ca_produit, ca_total)

        print(f"Fichier Excel créé : {OUTPUT_FILE}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
