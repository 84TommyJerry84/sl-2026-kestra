from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = "work/comptoir.duckdb"
OUTPUT_DIR = Path("outputs")


def charger_donnees(con):
    """Charge les données fusionnées depuis DuckDB."""
    query = """
        SELECT
            product_id,
            onsale_web,
            price,
            stock_quantity,
            stock_status,
            id_web,
            sku,
            post_type,
            post_title,
            total_sales
        FROM merged_data
    """

    return con.execute(query).df()


def calculer_zscore(df):
    """Calcule le z-score du prix pour chaque produit."""
    df = df.copy()

    df["price"] = pd.to_numeric(df["price"])

    moyenne_prix = df["price"].mean()
    ecart_type_prix = df["price"].std(ddof=0)

    df["zscore"] = (df["price"] - moyenne_prix) / ecart_type_prix

    return df, moyenne_prix, ecart_type_prix


def separer_vins(df):
    """Sépare les vins premium des vins ordinaires."""
    premium = df[df["zscore"] > 2].copy()
    ordinaire = df[df["zscore"] <= 2].copy()

    return premium, ordinaire


def exporter_csv(premium, ordinaire):
    """Exporte les deux catégories de vins au format CSV."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    premium.to_csv(
        OUTPUT_DIR / "vins_premium.csv",
        index=False,
    )

    ordinaire.to_csv(
        OUTPUT_DIR / "vins_ordinaires.csv",
        index=False,
    )


def main():
    con = duckdb.connect(DB_PATH)

    try:
        df = charger_donnees(con)

        df, moyenne_prix, ecart_type_prix = calculer_zscore(df)

        premium, ordinaire = separer_vins(df)

        print("Nombre de lignes :", len(df))
        print("Moyenne des prix :", moyenne_prix)
        print("Écart-type des prix :", ecart_type_prix)

        print(
            df[["product_id", "price", "zscore", "post_title"]]
            .sort_values("zscore", ascending=False)
            .head(50)
        )

        print("Nombre de vins premium :", len(premium))
        print("Nombre de vins ordinaires :", len(ordinaire))
        print("Total :", len(premium) + len(ordinaire))

        exporter_csv(premium, ordinaire)

        print("Fichier premium créé :", len(premium), "lignes")
        print("Fichier ordinaire créé :", len(ordinaire), "lignes")

    finally:
        con.close()


if __name__ == "__main__":
    main()
