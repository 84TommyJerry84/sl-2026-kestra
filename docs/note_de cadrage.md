# Note de cadrage

## Contexte

Le Comptoir des Coteaux souhaite automatiser le traitement réalisé manuellement chaque mois à partir de trois sources :

- un fichier ERP ;
- un fichier Web ;
- un fichier de liaison.

Le pipeline doit permettre de rapprocher les données ERP et Web, calculer le chiffre d'affaires et classer les vins à partir de leur z-score.

## Objectifs

Le pipeline doit :

- récupérer les trois fichiers sources ;
- identifier automatiquement les sources à partir de leurs colonnes ;
- accepter les formats CSV et XLSX ;
- nettoyer les données ;
- dédoublonner les enregistrements ;
- rapprocher les produits ERP et Web grâce au fichier de liaison ;
- calculer le chiffre d'affaires par produit ;
- calculer le chiffre d'affaires total ;
- calculer le z-score des prix ;
- séparer les vins premium et ordinaires ;
- produire les livrables dans le dossier local `outputs/`.

## Technologies retenues

L'orchestration est réalisée avec Kestra.

Les traitements de nettoyage, de dédoublonnage, de jointure et de calcul du chiffre d'affaires sont réalisés en SQL avec DuckDB.

Python avec pandas est utilisé pour :

- la préparation et l'identification des fichiers sources ;
- le calcul du z-score ;
- la génération des fichiers de sortie.

PostgreSQL est utilisé par Kestra pour son stockage interne.

L'ensemble de l'environnement est exécuté avec Docker Compose.

## Sources

Les fichiers sont déposés dans le dossier local `data/`.

Les noms des fichiers ne sont pas imposés.

Leur rôle est identifié à partir des colonnes présentes.

Les colonnes supplémentaires sont autorisées lorsqu'elles ne sont pas utilisées par le pipeline.

### ERP

Colonnes utilisées :

- `product_id`
- `onsale_web`
- `price`
- `stock_quantity`
- `stock_status`

### Liaison

Colonnes utilisées :

- `product_id`
- `id_web`

### Web

Colonnes utilisées :

- `sku`
- `post_type`
- `post_title`
- `total_sales`

## Qualité des données

La cartographie des données a montré que :

- l'ERP ne présente pas de valeurs manquantes sur les champs utilisés ;
- le fichier de liaison contient des lignes sans `id_web` ;
- le fichier Web contient des lignes sans `sku` ainsi que des doublons ;
- certaines lignes ne peuvent donc pas participer à la jointure.

Les lignes sans identifiant de liaison ou sans SKU ne sont pas considérées comme des erreurs bloquantes lorsqu'elles sont simplement non joignables.

En revanche, les données nécessaires aux enregistrements effectivement exploitables sont contrôlées.

Le pipeline contient également des contrôles sur :

- les valeurs manquantes ;
- les doublons ;
- la cohérence de la jointure ;
- le chiffre d'affaires ;
- le z-score.

## Règles métier

Le fichier de liaison permet de relier :

```text
ERP.product_id
        ↓
liaison.product_id
liaison.id_web
        ↓
Web.sku
```

Le chiffre d'affaires est calculé avec :

```text
chiffre_affaires = price × total_sales
```

Le classement statistique utilise le z-score :

```text
z = (prix - moyenne des prix) / écart-type
```

Règle de classification :

```text
z > 2     → vin premium
z <= 2    → vin ordinaire
```

## Livrables

Le pipeline produit :

```text
outputs/chiffre_affaires.xlsx
outputs/vins_premium.csv
outputs/vins_ordinaires.csv
```

Le fichier Excel contient :

- le chiffre d'affaires par produit ;
- le chiffre d'affaires total.

## Orchestration

Le pipeline peut être exécuté manuellement dans Kestra ou via :

```powershell
.\run.ps1
```

Une exécution automatique est planifiée le :

```text
15 de chaque mois à 09:00
timezone Europe/Paris
```

## Gestion des erreurs

Kestra orchestre les contrôles et les erreurs.

Des assertions vérifient les principales règles de qualité.

Les tâches Python critiques disposent également d'un mécanisme de retry.

Si un contrôle bloquant échoue, l'exécution Kestra se termine avec le statut `FAILED`.

Si tous les traitements et contrôles réussissent, l'exécution se termine avec le statut `SUCCESS`.