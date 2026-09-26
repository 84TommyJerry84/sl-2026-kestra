# Comptoir des Coteaux — Pipeline de traitement des ventes

## Contexte

Le Comptoir des Coteaux souhaite automatiser un traitement mensuel réalisé à partir de trois sources :

- un fichier ERP ;
- un fichier Web ;
- un fichier de liaison entre les identifiants ERP et Web.

Le pipeline :

1. identifie automatiquement les trois sources ;
2. vérifie leur structure ;
3. prépare les données ;
4. nettoie et dédoublonne les données avec DuckDB ;
5. rapproche les produits ERP avec les ventes Web ;
6. calcule le chiffre d'affaires par produit et le chiffre d'affaires total ;
7. calcule un z-score sur les prix ;
8. sépare les vins premium et ordinaires ;
9. exécute plusieurs contrôles de cohérence ;
10. publie les livrables dans le dossier local `outputs/`.

L'orchestration est réalisée avec **Kestra**.

La logique de traitement reste dans les scripts **SQL** et **Python**.

Une exécution automatique est planifiée le **15 de chaque mois à 09:00, heure de Paris**.

---

## Architecture

Les principaux outils utilisés sont :

- **Kestra** : orchestration, planification, assertions et gestion des erreurs ;
- **DuckDB** : nettoyage, dédoublonnage, jointure et calcul du chiffre d'affaires ;
- **Python / pandas** : préparation des sources et calcul du z-score ;
- **openpyxl** : lecture des fichiers XLSX et génération du rapport Excel ;
- **PostgreSQL** : stockage interne utilisé par Kestra ;
- **Docker Compose** : exécution reproductible de l'environnement ;
- **PowerShell** : lancement simplifié avec `run.ps1` ;
- **Git / GitHub** : versionnement du projet ;
- **OpenProject** : suivi du backlog et du Kanban.

Le principe retenu est le suivant :

```text
data/
  ↓
Kestra
  ↓
Python : identification et préparation des sources
  ↓
DuckDB : nettoyage / dédoublonnage / fusion / CA
  ↓
Python : z-score
  ↓
Contrôles dynamiques
  ↓
outputs/
```

---

## Structure du dépôt

```text
sl-2026-kestra/
├── data/
│   ├── Fichier_erp.xlsx
│   ├── Fichier_web.xlsx
│   └── fichier_liaison.xlsx
│
├── docs/
│   ├── rapport_openproject.pdf
│   └── ...
│
├── flows/
│   └── pipeline_comptoir.yaml
│
├── outputs/
│   ├── chiffre_affaires.xlsx
│   ├── vins_premium.csv
│   └── vins_ordinaires.csv
│
├── python/
│   ├── prepare_sources.py
│   ├── export_revenue.py
│   └── zscore.py
│
├── sql/
│   ├── etape1_clean.sql
│   ├── etape2_deduplicate.sql
│   ├── etape3_merge.sql
│   └── etape4_cal_revenue.sql
│
├── .env.example
├── .gitignore
├── docker-compose.yaml
├── requirements.txt
├── run.ps1
├── carto_data.ipynb
└── README.md
```

---

## Gestion des fichiers sources

Les fichiers métier sont déposés par l'utilisateur dans :

```text
data/
```

Le dossier doit contenir exactement trois sources :

- ERP ;
- liaison ;
- Web.

Les fichiers peuvent être :

```text
.csv
.xlsx
```

Les noms de fichiers ne sont pas utilisés pour déterminer leur rôle.

Le script :

```text
python/prepare_sources.py
```

identifie chaque source à partir de ses colonnes.

### Colonnes attendues

#### ERP

```text
product_id
onsale_web
price
stock_quantity
stock_status
```

#### Liaison

```text
product_id
id_web
```

#### Web

```text
sku
post_type
post_title
total_sales
```

Les colonnes supplémentaires sont autorisées et ignorées lorsqu'elles ne sont pas utiles au pipeline.

Par exemple, le fichier Web de référence contient de nombreuses colonnes supplémentaires sans empêcher son traitement.

Après identification, Python produit trois fichiers normalisés :

```text
prepared/erp.csv
prepared/liaison.csv
prepared/web.csv
```

utilisés ensuite par DuckDB.

---

## Gestion des valeurs absentes

La présence d'une colonne dans le schéma est obligatoire, mais certaines valeurs peuvent légitimement être absentes.

Par exemple :

- une ligne de liaison peut ne pas avoir de `id_web` si le produit ERP n'a pas de correspondance Web ;
- une ligne Web de type `product` peut ne pas avoir de `sku` et être non joignable.

Ces lignes sont comptabilisées dans les contrôles mais ne provoquent pas automatiquement un échec lorsqu'elles sont simplement non exploitables pour la jointure.

En revanche, les champs nécessaires sur les enregistrements réellement exploitables restent contrôlés.

---

## Prérequis

Pour exécuter le projet :

- Windows avec PowerShell ;
- Docker Desktop ;
- Docker Compose ;
- Git.

Versions utilisées pendant le développement :

- Kestra `2.0.3` ;
- kestractl `2.1.0` ;
- PostgreSQL `18` ;
- Python `3.12` dans les tâches du pipeline.

Les dépendances Python sont également décrites dans :

```text
requirements.txt
```

---

## Installation

### 1. Cloner le dépôt

```powershell
git clone https://github.com/84TommyJerry84/sl-2026-kestra.git
cd sl-2026-kestra
```

### 2. Créer le fichier `.env`

```powershell
Copy-Item .env.example .env
```

Puis renseigner les variables nécessaires dans `.env`.

Exemple :

```env
POSTGRES_PASSWORD=...
KESTRA_USERNAME=...
KESTRA_PASSWORD=...
```

Le fichier `.env` contient les secrets locaux et n'est pas versionné.

---

## Lancement recommandé

Le moyen le plus simple d'exécuter tout le projet est :

```powershell
.\run.ps1
```

Le script réalise automatiquement les étapes suivantes :

```text
vérification des sources
        ↓
vérification de Docker
        ↓
démarrage PostgreSQL + Kestra
        ↓
redéploiement du flow
        ↓
import des scripts SQL
        ↓
import des scripts Python
        ↓
lancement du pipeline Kestra
        ↓
attente de la fin de l'exécution
        ↓
vérification du statut SUCCESS
        ↓
vérification des 3 livrables
```

Une exécution correcte se termine par :

```text
========================================
 PIPELINE TERMINE AVEC SUCCES
========================================
```

Le script ne supprime pas les volumes Docker existants.

---

## Démarrage manuel de l'environnement

Il est également possible de démarrer les services manuellement :

```powershell
docker compose up -d
```

Les principaux services sont :

- `postgres` ;
- `kestra` ;
- `kestra-init`.

`kestra-init` est un conteneur ponctuel.

Lorsqu'il a terminé correctement :

```text
kestra-init    Exited (0)
```

Cela signifie que le flow et les fichiers nécessaires ont été déployés avec succès.

Vérification :

```powershell
docker compose ps -a
```

Logs :

```powershell
docker compose logs kestra-init
```

---

## Initialisation Kestra

`kestra-init` :

1. attend que Kestra soit disponible ;
2. déploie `flows/pipeline_comptoir.yaml` ;
3. importe les quatre scripts SQL ;
4. importe les trois scripts Python.

Les données métier du dossier `data/` ne sont pas copiées dans les Namespace Files.

Le dossier local est monté dans le conteneur Kestra et lu lors de chaque exécution.

Cela permet à l'utilisateur de remplacer les trois sources par les fichiers du mois suivant sans reconstruire l'image Docker.

Namespace :

```text
comptoir.coteaux
```

Flow :

```text
pipeline_comptoir
```

---

## Interface Kestra

L'interface est accessible à :

```text
http://localhost:8082
```

Une exécution manuelle peut être lancée depuis :

```text
Flows
→ comptoir.coteaux
→ pipeline_comptoir
→ Execute
```

Le résultat attendu est :

```text
SUCCESS
```

---

## Enchaînement du pipeline

```text
Lecture de data/
        ↓
Identification ERP / liaison / Web
        ↓
Conversion en CSV normalisés
        ↓
Nettoyage DuckDB
        ↓
Contrôle des valeurs manquantes
        ↓
Dédoublonnage
        ↓
Contrôle des doublons
        ↓
Fusion ERP / liaison / Web
        ↓
Contrôle de la jointure
        ↓
Calcul du chiffre d'affaires
        ↓
Contrôle du chiffre d'affaires
        ↓
Calcul du z-score
        ↓
Contrôle du z-score
        ↓
Export Excel
        ↓
Publication dans outputs/
```

---

## Tests intégrés

Le pipeline ne dépend pas de valeurs fixes propres à un mois donné.

Les contrôles de production sont dynamiques.

### Valeurs manquantes

Contrôle des champs nécessaires sur les lignes métier exploitables.

### Doublons

Vérification de l'unicité des clés après dédoublonnage.

### Jointure

Vérification notamment :

- de la présence de lignes fusionnées ;
- de l'unicité des `product_id` ;
- de l'unicité des `sku` ;
- de la cohérence entre `id_web` et `sku`.

### Chiffre d'affaires

Pour chaque ligne :

```text
chiffre_affaires = price × total_sales
```

Le pipeline vérifie également que le chiffre d'affaires global correspond à la somme des chiffres d'affaires par produit.

### Z-score

Le z-score est calculé avec :

```text
z = (prix - moyenne des prix) / écart-type
```

Classification :

```text
z > 2     → premium
z <= 2    → ordinaire
```

Le pipeline contrôle :

- la cohérence du z-score ;
- la cohérence de la classification ;
- l'absence de perte de lignes pendant la séparation.

---

## Retry et gestion des erreurs

Les principales tâches Python disposent d'un mécanisme de retry.

En cas d'échec, Kestra journalise l'erreur et l'exécution se termine avec un statut `FAILED`.

Avec `run.ps1`, les logs d'erreur Kestra sont affichés automatiquement si l'exécution échoue.

---

## Planification automatique

Le flow contient le trigger suivant :

```yaml
triggers:
  - id: lancement_mensuel
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 9 15 * *"
    timezone: Europe/Paris
```

Le pipeline est donc exécuté automatiquement :

```text
le 15 de chaque mois
à 09:00
timezone Europe/Paris
```

Il reste également exécutable manuellement.

---

## Livrables

Le pipeline publie réellement les fichiers dans le dossier local :

```text
outputs/
```

avec :

```text
outputs/chiffre_affaires.xlsx
outputs/vins_premium.csv
outputs/vins_ordinaires.csv
```

### `chiffre_affaires.xlsx`

Contient deux feuilles :

```text
CA_par_produit
CA_total
```

### `vins_premium.csv`

Contient les produits dont :

```text
zscore > 2
```

### `vins_ordinaires.csv`

Contient les produits dont :

```text
zscore <= 2
```

---

## Validation sur plusieurs jeux de données

Le pipeline a été testé avec deux jeux différents afin de vérifier qu'il ne dépend pas de valeurs codées en dur.

### Jeu de test CSV

Résultats :

| Contrôle | Résultat |
|---|---:|
| Produits fusionnés | 48 |
| Chiffre d'affaires total | 5 443,70 € |
| Vins premium | 3 |
| Vins ordinaires | 45 |

Le pipeline s'est terminé avec :

```text
SUCCESS
```

### Jeu de référence Octave XLSX

Résultats :

| Contrôle | Résultat |
|---|---:|
| Produits fusionnés | 714 |
| Chiffre d'affaires total | 70 568,60 € |
| Vins premium | 30 |
| Vins ordinaires | 684 |
| Liaisons sans `id_web` | 91 |
| Produits Web sans `sku` | 2 |

Le pipeline s'est également terminé avec :

```text
SUCCESS
```

Les valeurs :

```text
714
70 568,60 €
30
684
```

sont utilisées comme valeurs de référence pour le jeu Octave uniquement.

Elles ne sont pas codées comme assertions dans le pipeline de production.

---

## Formats testés

Le pipeline a été validé avec :

```text
CSV
XLSX
```

Les fichiers peuvent porter des noms différents, car les sources sont identifiées par leur schéma et non par leur nom.

---

## Arrêter l'environnement

Pour arrêter les conteneurs tout en conservant les volumes :

```powershell
docker compose down
```

Les données persistantes sont conservées.

La commande suivante supprimerait également les volumes :

```powershell
docker compose down -v
```

Elle n'est pas nécessaire pour une utilisation normale du projet.

---

## Documentation

Le dossier `docs/` contient notamment :

- les documents de cadrage ;
- les diagrammes du pipeline ;
- les captures d'écran ;
- la documentation du suivi du projet ;
- le rapport OpenProject.

Le suivi OpenProject est disponible dans :

```text
docs/rapport_openproject.pdf
```

---

## Sécurité

Les secrets locaux sont placés dans :

```text
.env
```

Ce fichier est exclu du dépôt Git.

Le dépôt versionne uniquement :

```text
.env.example
```

qui sert de modèle de configuration.

---

## Résumé d'utilisation

Pour une utilisation mensuelle :

1. déposer les trois nouvelles sources CSV ou XLSX dans `data/` ;
2. vérifier qu'il n'y a que trois sources métier dans ce dossier ;
3. lancer :

```powershell
.\run.ps1
```

4. attendre :

```text
PIPELINE TERMINE AVEC SUCCES
```

5. récupérer les résultats dans :

```text
outputs/
```