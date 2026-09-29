# Comptoir des Coteaux — Pipeline de traitement des ventes

## Contexte

Le projet automatise un traitement mensuel à partir de trois sources : **ERP**, **Web** et **liaison**.

Le pipeline identifie les fichiers, valide leur schéma, nettoie et dédoublonne les données, fusionne ERP et Web via la table de liaison, calcule le chiffre d'affaires, calcule le z-score des prix, sépare les vins premium et ordinaires puis publie les livrables dans `outputs/`.

**Kestra orchestre ; la logique métier reste dans SQL DuckDB et Python/pandas.**

Exécution automatique : **le 15 de chaque mois à 09:00, Europe/Paris**.

---

## Architecture

| Outil | Rôle |
|---|---|
| Kestra | orchestration, cron, assertions, retry, erreurs |
| DuckDB / SQL | nettoyage, dédoublonnage, jointure, CA |
| Python / pandas | identification des sources, préparation, z-score |
| openpyxl | lecture XLSX et génération Excel |
| PostgreSQL | stockage interne de Kestra |
| Docker Compose | environnement local reproductible |
| PowerShell | lancement complet avec `run.ps1` |
| OpenProject | backlog et Kanban |

```text
data/
  ↓
Identification + validation
  ↓
Préparation CSV normalisés
  ↓
Nettoyage → test valeurs manquantes
  ↓
Dédoublonnage → test doublons
  ↓
Fusion → test jointure
  ↓
Calcul CA → test CA
  ↓
Z-score + séparation → test z-score
  ↓
outputs/
```

Logigramme :
- `docs/Diagramme_pipeline.drawio`
- `docs/Diagramme_pipeline.png`

---

## Structure du dépôt

```text
sl-2026-kestra/
├── data/
├── docs/
│   ├── Diagramme_pipeline.drawio
│   ├── Diagramme_pipeline.png
│   ├── rapport_openproject.pdf
│   └── screenshots/
├── flows/pipeline_comptoir.yaml
├── outputs/
│   ├── chiffre_affaires.xlsx
│   ├── vins_premium.csv
│   └── vins_ordinaires.csv
├── python/
│   ├── prepare_sources.py
│   ├── export_revenue.py
│   └── zscore.py
├── sql/
│   ├── etape1_clean.sql
│   ├── etape2_deduplicate.sql
│   ├── etape3_merge.sql
│   └── etape4_cal_revenue.sql
├── soutenance/Presentation_Comptoir_des_Coteaux.pptx
├── docker-compose.yaml
├── run.ps1
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Données d'entrée

`data/` doit contenir **exactement trois sources**, en `.csv` ou `.xlsx`.

Les noms de fichiers sont libres : `python/prepare_sources.py` identifie leur rôle grâce aux colonnes.

| Source | Colonnes obligatoires |
|---|---|
| ERP | `product_id`, `onsale_web`, `price`, `stock_quantity`, `stock_status` |
| Liaison | `product_id`, `id_web` |
| Web | `sku`, `post_type`, `post_title`, `total_sales` |

Les colonnes supplémentaires sont autorisées.

Après validation, Python génère :

```text
prepared/erp.csv
prepared/liaison.csv
prepared/web.csv
```

Les lignes Web sans `sku` exploitable sont supprimées au nettoyage. Une liaison sans `id_web` peut être conservée si le produit ERP n'a pas de correspondance Web.

---

## Installation et lancement

### Prérequis

- Docker Desktop ;
- Docker Compose ;
- Git ;
- PowerShell.

Versions utilisées :
- Kestra `2.0.3`
- kestractl `2.1.0`
- PostgreSQL `18`
- Python `3.12`

### Installation

```powershell
git clone https://github.com/84TommyJerry84/sl-2026-kestra.git
cd sl-2026-kestra
Copy-Item .env.example .env
```

Compléter `.env` :

```env
POSTGRES_PASSWORD=...
KESTRA_USERNAME=...
KESTRA_PASSWORD=...
```

`.env` n'est pas versionné.

### Lancement recommandé

Après avoir déposé les trois fichiers dans `data/` :

```powershell
.\run.ps1
```

Le script démarre l'environnement, déploie le flow et les scripts, exécute le pipeline, attend le statut final et vérifie les trois livrables.

Résultat attendu :

```text
PIPELINE TERMINE AVEC SUCCES
```

### Lancement depuis Kestra

```powershell
docker compose up -d
```

Interface :

```text
http://localhost:8082
```

Puis :

```text
Flows → comptoir.coteaux → pipeline_comptoir → Execute
```

---

## Contrôles de qualité

Les tests sont **dynamiques** : les valeurs Octave ne sont pas codées en dur dans le pipeline.

| Test | Contrôle |
|---|---|
| Valeurs manquantes | champs obligatoires sur les lignes exploitables |
| Doublons | unicité des clés après dédoublonnage |
| Jointure | unicité `product_id` / `sku` et cohérence `id_web = sku` |
| Chiffre d'affaires | `CA = price × total_sales` et cohérence du total |
| Z-score | formule, classification et absence de perte de lignes |

Formule :

```text
z = (prix - moyenne des prix) / écart-type
```

Classification :

```text
z > 2  → premium
z <= 2 → ordinaire
```

Les principales tâches Python disposent d'un retry. En cas d'échec, Kestra journalise l'erreur et l'exécution passe en `FAILED`.

---

## Planification

```yaml
cron: "0 9 15 * *"
timezone: Europe/Paris
```

Le pipeline reste également exécutable manuellement.

---

## Livrables

```text
outputs/chiffre_affaires.xlsx
outputs/vins_premium.csv
outputs/vins_ordinaires.csv
```

`chiffre_affaires.xlsx` contient :
- `CA_par_produit`
- `CA_total`

---

## Validation

### Jeu de référence Octave

| Étape | Référence | Pipeline |
|---|---:|---:|
| ERP après dédoublonnage | 825 | 825 |
| Liaison après dédoublonnage | 825 | 825 |
| Web après nettoyage | 1 428 | 1 428 |
| Web après dédoublonnage | 714 | 714 |
| Fichier fusionné | 714 | 714 |
| CA total | 70 568,60 € | 70 568,60 € |
| Vins premium | 30 | 30 |
| Vins ordinaires | 684 | 684 |

Ces valeurs servent uniquement à valider le jeu fourni par Octave.

### Deuxième jeu CSV

| Contrôle | Résultat |
|---|---:|
| Produits fusionnés | 48 |
| CA total | 5 443,70 € |
| Vins premium | 3 |
| Vins ordinaires | 45 |

Ce test confirme que le pipeline fonctionne avec des données et résultats différents.

---

## Documentation

Le dossier `docs/` contient le cadrage, le logigramme, les captures Kestra et l'export OpenProject.

L'instance OpenProject ayant été auto-hébergée localement, elle n'est pas accessible publiquement. Son export est disponible ici :

[Consulter le rapport OpenProject](docs/rapport_openproject.pdf)

Support de soutenance :

```text
soutenance/Presentation_Comptoir_des_Coteaux.pptx
```

---

## Sécurité

- secrets dans `.env` ;
- `.env` exclu par `.gitignore` ;
- `.env.example` seul est versionné.

---

## Arrêt

```powershell
docker compose down
```

Les volumes sont conservés.
