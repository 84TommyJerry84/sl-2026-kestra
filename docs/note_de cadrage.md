# Note de cadrage

# Note de cadrage

Le but du projet est d'automatiser le traitement que faisait Octave manuellement tous les mois.

On doit récupérer les trois fichiers ERP, Web et liaison, puis les nettoyer avant de pouvoir les utiliser.

Le fichier de liaison va permettre de faire le lien entre l'identifiant `product_id` de l'ERP et l'identifiant du Web.

Le pipeline devra ensuite calculer le chiffre d'affaires par produit ainsi que le chiffre d'affaires total.

Il devra aussi séparer les vins premium et les vins ordinaires grâce au calcul du z-score.

À la fin, on doit produire un rapport Excel pour le chiffre d'affaires et deux fichiers CSV pour les vins premium et ordinaires.
Le pipeline sera orchestré avec Kestra et devra se lancer automatiquement le 15 de chaque mois à 9h.

Les traitements de nettoyage, dédoublonnage, jointure et calcul du CA seront faits en SQL avec DuckDB.

Python avec pandas sera utilisé pour la partie statistique du z-score.
Lors de la cartographie, l'ERP ne présente pas de valeurs manquantes ni de doublons sur `product_id`.

Le fichier Web contient des valeurs `sku` manquantes et des doublons, il devra donc être nettoyé avant la jointure.

Le fichier de liaison contient également des valeurs `id_web` manquantes même si les identifiants renseignés sont uniques.

Les points à clarifier sont la façon exacte de gérer les lignes sans identifiant, le dédoublonnage du fichier Web et le comportement du pipeline si une tâche ou un service comme DuckDB tombe en erreur.