from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = Path("work/comptoir.duckdb")
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

    try:
        df["price"] = pd.to_numeric(df["price"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError(
            "La colonne 'price' contient au moins une valeur non numérique."
        ) from exc

    if df["price"].isna().any():
        raise ValueError("La colonne 'price' contient au moins une valeur manquante.")

    if df.empty:
        raise ValueError("Impossible de calculer le z-score : aucune ligne fusionnée.")

    moyenne_prix = df["price"].mean()
    ecart_type_prix = df["price"].std(ddof=0)

    # Cas valide : tous les produits ont exactement le même prix.
    # Leur distance à la moyenne est donc nulle.
    if ecart_type_prix == 0:
        df["zscore"] = 0.0
    else:
        df["zscore"] = (df["price"] - moyenne_prix) / ecart_type_prix

    if df["zscore"].isna().any():
        raise ValueError("Le calcul du z-score a produit des valeurs manquantes.")

    return df, moyenne_prix, ecart_type_prix


def separer_vins(df):
    """Sépare les vins premium des vins ordinaires."""
    premium = df[df["zscore"] > 2].copy()
    ordinaire = df[df["zscore"] <= 2].copy()

    if len(premium) + len(ordinaire) != len(df):
        raise ValueError("La séparation premium/ordinaire a perdu des lignes.")

    return premium, ordinaire


def exporter_csv(premium, ordinaire):
    """Exporte les deux catégories de vins au format CSV."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    premium.to_csv(
        OUTPUT_DIR / "vins_premium.csv",
        index=False,
        encoding="utf-8",
    )

    ordinaire.to_csv(
        OUTPUT_DIR / "vins_ordinaires.csv",
        index=False,
        encoding="utf-8",
    )


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Base DuckDB introuvable : {DB_PATH}")

    con = duckdb.connect(str(DB_PATH))

    try:
        df = charger_donnees(con)

        df, moyenne_prix, ecart_type_prix = calculer_zscore(df)

        premium, ordinaire = separer_vins(df)

        print("Nombre de lignes :", len(df))
        print("Moyenne des prix :", moyenne_prix)
        print("Écart-type des prix :", ecart_type_prix)
        print("Nombre de vins premium :", len(premium))
        print("Nombre de vins ordinaires :", len(ordinaire))
        print("Total :", len(premium) + len(ordinaire))

        exporter_csv(premium, ordinaire)

        print(
            "Fichier premium créé :",
            len(premium),
            "lignes",
        )
        print(
            "Fichier ordinaire créé :",
            len(ordinaire),
            "lignes",
        )

    finally:
        con.close()


if __name__ == "__main__":
    main()
