# Comptoir des Coteaux — Pipeline de traitement des ventes

## Contexte

Le Comptoir des Coteaux souhaite automatiser un traitement réalisé chaque mois à partir de trois fichiers issus de l'ERP, du site Web et d'une table de liaison.

Le pipeline nettoie et dédoublonne les données, rapproche les produits ERP avec les ventes Web, calcule le chiffre d'affaires par produit et le chiffre d'affaires total, puis classe les vins selon leur z-score.

L'orchestration est réalisée avec **Kestra**. Les traitements de données sont effectués avec **DuckDB en SQL** et la partie statistique avec **Python et pandas**.

Le pipeline produit un rapport Excel du chiffre d'affaires ainsi que deux fichiers CSV contenant les vins premium et les vins ordinaires.

Une exécution automatique est prévue le **15 de chaque mois à 9 h, heure de Paris**.

## Architecture

Les principaux outils utilisés sont :

- **Kestra** : orchestration, planification et gestion des erreurs ;
- **DuckDB** : nettoyage, dédoublonnage, jointure et calcul du chiffre d'affaires ;
- **Python / pandas** : calcul du z-score et séparation des vins ;
- **openpyxl** : génération du rapport Excel ;
- **PostgreSQL** : stockage interne utilisé par Kestra ;
- **Docker Compose** : lancement reproductible de l'environnement ;
- **Git / GitHub** : versionnement du projet ;
- **OpenProject** : suivi du backlog et du Kanban.

Kestra orchestre les traitements mais la logique métier reste dans les scripts SQL et Python.

## Structure du dépôt

```text
sl-2026-kestra/
├── data/
│   ├── Fichier_erp.xlsx
│   ├── Fichier_web.xlsx
│   └── fichier_liaison.xlsx
├── docs/
│   ├── note_cadrage.md
│   ├── logigramme_pipeline.drawio
│   └── ...
├── flows/
│   └── pipeline_comptoir.yaml
├── outputs/
│   ├── chiffre_affaires.xlsx
│   ├── vins_premium.csv
│   └── vins_ordinaires.csv
├── python/
│   ├── export_revenue.py
│   └── zscore.py
├── sql/
│   ├── etape1_clean.sql
│   ├── etape2_deduplicate.sql
│   ├── etape3_merge.sql
│   └── etape4_cal_revenue.sql
├── .env.example
├── .gitignore
├── docker-compose.yaml
├── requirements.txt
├── carto_data.ipynb
└── README.md
```

## Prérequis

Pour relancer le pipeline :

- Docker Desktop ;
- Docker Compose ;
- Git ;
- un navigateur Web.

Versions utilisées pendant le développement :

- Docker 29.7.2 ;
- Docker Compose v5.4.0 ;
- Kestra 2.0.3 ;
- kestractl 2.1.0 ;
- PostgreSQL 18 ;
- Python 3.12 pour les tâches Python du pipeline.

Les dépendances Python du projet sont également figées dans `requirements.txt`.

## Installation et lancement

### 1. Cloner le dépôt

```powershell
git clone https://github.com/84TommyJerry84/sl-2026-kestra.git
cd sl-2026-kestra
```

### 2. Créer le fichier d'environnement

Copier le fichier d'exemple :

```powershell
Copy-Item .env.example .env
```

Puis renseigner dans `.env` les mots de passe souhaités :

```env
POSTGRES_PASSWORD=...
KESTRA_USERNAME=admin@kestra.io
KESTRA_PASSWORD=...
```

Le fichier `.env` contient les secrets locaux et n'est pas versionné dans Git.

### 3. Lancer l'environnement

Depuis la racine du dépôt :

```powershell
docker compose up -d
```

Docker Compose démarre trois services :

- `postgres` : base utilisée par Kestra ;
- `kestra` : serveur d'orchestration ;
- `kestra-init` : initialisation automatique du projet.

Vérifier leur état :

```powershell
docker compose ps -a
```

Après l'initialisation, le résultat attendu est notamment :

```text
kestra           Up
postgres         Up (healthy)
kestra-init      Exited (0)
```

`kestra-init` est un conteneur ponctuel : le statut `Exited (0)` indique que son travail s'est terminé correctement.

Les logs peuvent être consultés avec :

```powershell
docker compose logs kestra-init
```

## Initialisation automatique de Kestra

Lors du premier démarrage, `kestra-init` :

1. attend que Kestra soit disponible ;
2. déploie automatiquement `flows/pipeline_comptoir.yaml` ;
3. importe les trois fichiers sources dans les Namespace Files ;
4. importe les quatre scripts SQL ;
5. importe les deux scripts Python.

Le namespace utilisé est :

```text
comptoir.coteaux
```

et le flow :

```text
pipeline_comptoir
```

Aucun import manuel du flow ou des Namespace Files n'est nécessaire.

L'interface Kestra est accessible à l'adresse :

[http://localhost:8082](http://localhost:8082)

La connexion s'effectue avec `KESTRA_USERNAME` et `KESTRA_PASSWORD` définis dans le fichier `.env`.

## Exécuter le pipeline

Dans l'interface Kestra :

1. ouvrir **Flows** ;
2. ouvrir le namespace `comptoir.coteaux` ;
3. sélectionner `pipeline_comptoir` ;
4. lancer une exécution avec **Execute** ;
5. vérifier que l'exécution se termine avec le statut `SUCCESS`.

Le pipeline suit principalement cet enchaînement :

```text
Sources ERP / Web / liaison
        ↓
Nettoyage
        ↓
Test des valeurs manquantes
        ↓
Dédoublonnage
        ↓
Test des doublons
        ↓
Fusion ERP / liaison / Web
        ↓
Test de la jointure
        ↓
Calcul du chiffre d'affaires
        ↓
Test du chiffre d'affaires
        ↓
Calcul du z-score
        ↓
Test du z-score
        ↓
Exports
```

Chaque contrôle métier est suivi d'une assertion Kestra. Si une assertion échoue, l'exécution passe en erreur.

## Planification automatique

Le workflow contient un trigger :

```yaml
triggers:
  - id: lancement_mensuel
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 9 15 * *"
    timezone: Europe/Paris
```

Le pipeline est donc déclenché automatiquement le **15 de chaque mois à 9 h**.

## Tests intégrés

Cinq familles de contrôles sont intégrées au workflow :

- valeurs manquantes après nettoyage ;
- doublons après dédoublonnage ;
- cohérence de la jointure ERP / liaison / Web ;
- cohérence du chiffre d'affaires ;
- cohérence de la classification par z-score.

Les tâches Python disposent également d'un mécanisme de retry avec un maximum de trois tentatives.

Un gestionnaire global journalise les erreurs lorsqu'une exécution échoue.

Les mécanismes d'erreur et de retry ont été testés volontairement en provoquant l'échec d'une tâche.

## Résultats obtenus

Les résultats ont été comparés aux valeurs de référence fournies par Octave.

| Contrôle | Référence Octave | Résultat obtenu |
| --- | ---: | ---: |
| ERP après dédoublonnage | 825 lignes | 825 lignes |
| Liaison après dédoublonnage | 825 lignes | 825 lignes |
| Web après nettoyage | 1 428 lignes | 1 428 lignes |
| Web après dédoublonnage | 714 lignes | 714 lignes |
| Fichier fusionné | 714 lignes | 714 lignes |
| Chiffre d'affaires total | 70 568,60 € | 70 568,60 € |
| Vins premium (`z > 2`) | 30 | 30 |

Les résultats obtenus correspondent donc aux valeurs de référence fournies dans le brief.

## Fichiers produits

Le pipeline produit :

```text
outputs/chiffre_affaires.xlsx
outputs/vins_premium.csv
outputs/vins_ordinaires.csv
```

Résultats finaux :

- `chiffre_affaires.xlsx` : 714 produits, chiffre d'affaires total de **70 568,60 €** ;
- `vins_premium.csv` : **30 vins premium** ;
- `vins_ordinaires.csv` : **684 vins ordinaires**.

Les fichiers générés lors d'une exécution sont également disponibles dans les outputs des tâches Kestra correspondantes.

## Reproductibilité

La procédure Docker Compose a été testée avec des volumes Docker entièrement neufs afin de simuler une installation vierge.

À partir du dépôt et d'un fichier `.env`, la commande :

```powershell
docker compose up -d
```

a permis de :

```text
créer PostgreSQL
→ démarrer Kestra
→ déployer automatiquement le flow
→ importer les données
→ importer les scripts SQL
→ importer les scripts Python
→ exécuter le pipeline
→ SUCCESS
```

Lors de ce test sur une installation vierge, toutes les tâches du pipeline se sont exécutées avec succès.

## Arrêter le projet

Pour arrêter les conteneurs tout en conservant les données :

```powershell
docker compose down
```

Les volumes Docker sont conservés.

Pour supprimer également les volumes :

```powershell
docker compose down -v
```

Cette seconde commande supprime les données persistées par PostgreSQL et Kestra.

## Documentation

Le dossier `docs/` regroupe notamment :

- la note de cadrage ;
- le logigramme au format Draw.io ;
- l'image du logigramme ;
- les captures d'écran de Kestra ;
- les captures liées aux tests et à la gestion des erreurs.

## Suivi OpenProject

Le suivi du projet a été réalisé avec OpenProject : backlog, Kanban, planification des tâches et suivi de l'avancement.

Une exportation du suivi final est disponible dans le dépôt :

[Consulter le suivi OpenProject au format PDF](docs/openproject_suivi.pdf)

L'instance OpenProject utilisée pendant le projet a été auto-hébergée avec Docker.

## Sécurité

Les mots de passe ne sont pas stockés dans le dépôt.

Le fichier `.env` est exclu par `.gitignore`.

Seul `.env.example`, contenant des valeurs d'exemple, est versionné.