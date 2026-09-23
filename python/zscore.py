from pathlib import Path

import duckdb
import pandas as pd

# connexion avec à duckdb

con = duckdb.connect("work/comptoir.duckdb")

# recuperation de la data mergée

df = con.execute(
    """
    SELECT *
    FROM merged_data
    """
).df()

# cast du prix en nombre


df["price"] = pd.to_numeric(df["price"])


# petits print histoire d'afficher les resultats

print("Nombre de lignes :", len(df))
print("Type de price :", df["price"].dtype)
print(df[["product_id", "price", "post_title"]].head())

# moyenne et ecart type

moyenne_prix = df["price"].mean()
ecart_type_prix = df["price"].std(ddof=0)

# affichage des deux valeurs calculées
print("Moyenne des prix :", moyenne_prix)
print("Écart-type des prix :", ecart_type_prix)

# calcul du zscore comme dans le brief
df["zscore"] = (df["price"] - moyenne_prix) / ecart_type_prix

print(
    df[["product_id", "price", "zscore", "post_title"]]
    .sort_values("zscore", ascending=False)
    .head(30)
)
# tri sort et affichage
premium = df[df["zscore"] > 2].copy()
ordinaire = df[df["zscore"] <= 2].copy()

print("Nombre de vins premium :", len(premium))
print("Nombre de vins ordinaires :", len(ordinaire))
print("Total :", len(premium) + len(ordinaire))

# export des resultats en fichiers csv

# création du dossier de sortie ou cas ou il est apsss là
Path("outputs").mkdir(exist_ok=True)

# export des deux catégories
premium.to_csv("outputs/vins_premium.csv", index=False)
ordinaire.to_csv("outputs/vins_ordinaires.csv", index=False)

# print pour voir si les exports se sont bien faits
print("Fichier premium créé :", len(premium), "lignes")
print("Fichier ordinaire créé :", len(ordinaire), "lignes")

con.close()
