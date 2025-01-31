# CHS-CSB-Processing

CHS-CSB-Processing est présentement en développement. Plusieurs fonctionnalités sont encore incomplètes ou en cours de développement.
Vous pouvez visiter la [documentation](https://chs-csb-processing.readthedocs.io/fr/latest/) pour plus d'informations.

---

# Table des matières

- [CHS-CSB-Processing](#chs-csb-processing)
- [Tutoriel d'utilisation de l'interface en ligne de commande pour le traitement des fichiers bathymétriques](#tutoriel-dutilisation-de-linterface-en-ligne-de-commande-pour-le-traitement-des-fichiers-bathymétriques)
  - [Description](#description)
  - [Commande principale](#commande-principale)
    - [Options disponibles](#options-disponibles)
      - [`files`](#files)
      - [`--output`](#--output)
      - [`--vessel`](#--vessel)
      - [`--waterline`](#--waterline)
      - [`--config`](#--config)
      - [`--apply-water-level`](#--apply-water-level)
  - [Fichier de configuration (TOML)](#fichier-de-configuration-toml)
    - [Sections principales](#sections-principales)
  - [Fichier des navires (Vessels)](#fichier-des-navires-vessels)
    - [Description des champs](#description-des-champs)
  - [Gestion des erreurs](#gestion-des-erreurs)
    - [Fichiers invalides](#fichiers-invalides)
    - [Paramètres manquants](#paramètres-manquants)
  - [Exemple d'utilisation complet](#exemple-dutilisation-complet)
    - [Commande](#commande)
    - [Étapes détaillées](#étapes-détaillées)

---

# Tutoriel d'utilisation de l'interface en ligne de commande pour le traitement des fichiers bathymétriques

Ce tutoriel explique en détail comment utiliser le module de ligne de commande pour traiter et géoréférencer des fichiers 
de données bathymétriques. Il couvre chaque paramètre et fournit des exemples pratiques.

---

## Description

Ce module est conçu pour automatiser le traitement des fichiers de données bathymétriques. Il permet de :
- Identifier et charger les fichiers appropriés (CSV, TXT, XYZ).
- Effectuer un géoréférencement basé sur des configurations spécifiques.
- Gérer les identifiants de navires et les configurations associées.

Les formats de fichiers pris en charge sont les suivants : 
- OFM : extension `.xyz` avec minimalement les colonnes `LON`, `LAT`, `DEPTH`, `TIME` dans l'entête.
- DCDB : extension `.csv` avec minimalement les colonnes `LON`, `LAT`, `DEPTH`, `TIME` dans l'entête.
- Lowrance: extension `.csv` avec minimalement les colonnes `Longitude[°WGS84]`, `Latitude[°WGS84]`, `WaterDepth[Feet]`, 
            `DateTime[UTC]` dans l'entête. Ces fichiers sont le résultat des fichiers `SL3` de Lowrance exportés par 
            l'outil [SL3Reader](https://github.com/halmaia/SL3Reader).
- Actisense : à venir.
- BlackBox : à venir.

---

## Commande principale

```bash
python cli.py <files> [options] 
```

### Options disponibles

#### `files`
- **Description** : Spécifie les chemins des fichiers ou des répertoires à traiter.
- **Type** : `Collection[Path]`
- **Obligatoire** : Oui
- **Détails** : Vous pouvez fournir un ou plusieurs chemins. Si un répertoire est spécifié, tous les fichiers valides qu'il contient seront inclus.
- **Exemple** :
  ```bash
  python cli.py /data/fichier1.csv /data/dossier
  ```

#### `--output`
- **Description** : Spécifie le répertoire de sortie pour les fichiers traités.
- **Type** : `Path`
- **Obligatoire** : Oui
- **Détails** : Si ce paramètre n'est pas défini, le script ne pourra pas enregistrer les fichiers traités.
- **Exemple** :
  ```bash
  python cli.py /data/fichier1.csv --output /data/output
  ```

#### `--vessel`
- **Description** : Fournit l'identifiant du navire pour le traitement.
- **Type** : `str`
- **Obligatoire** : Non
- **Détails** : Si aucun identifiant n'est fourni, un navire par défaut avec des bras de levier à 0 sera utilisé.
- **Exemple** :
  ```bash
  python cli.py /data/fichier1.csv --vessel NAVIRE123
  ```

#### `--waterline`
- **Description** : Spécifie la distance entre le sondeur et la ligne d'eau.
- **Type** : `float`
- **Obligatoire** : Non
- **Détails** : Si ce paramètre est omis, une ligne d'eau à 0 sera utilisée. 
- **Exemple** :
  ```bash
  python cli.py /data/fichier1.csv --waterline 1.4
  ```


#### `--config`
- **Description** : Spécifie le chemin du fichier de configuration (au format TOML).
- **Type** : `Path`
- **Obligatoire** : Non
- **Détails** : Si ce paramètre est omis, un fichier de configuration par défaut sera utilisé.
- **Exemple** :
  ```bash
  python cli.py /data/fichier1.csv --config /config/config.toml
  ```

#### `--apply-water-level`
- **Description** : Active ou désactive la réduction des niveaux d'eau au zéro des cartes lors du géoréférencement.
- **Type** : `bool`
- **Obligatoire** : Non
- **Détails** : Si ce paramètre est omis, le géoréférencement basé sur les niveaux d'eau sera appliqué.
- **Exemple** :
  ```bash
  python cli.py /data/fichier1.csv --apply-water-level True
  ```
  
---

## Fichier de configuration (TOML)

Le fichier de configuration au format TOML permet de définir les paramètres pour le traitement. 
Voici un exemple du fichier de configuration par défaut (./src/CONFIG_csb-processing.toml) :

```toml
[IWLS.API.TimeSeries]
priority = ["wlo", "wlp"]  # Priorité des séries temporelles à récupérer.
max_time_gap = "1 min"  # Intervalle maximal sans données avant interpolation.
threshold_interpolation_filling = "4 h"  # Seuil pour interpolation et remplissage des données manquantes.
wlo_qc_flag_filter = ["NOT_EVAL", "QUESTIONABLE", "BAD", "MISSING", "2", "3"]  # Filtres de qualité pour wlo.
buffer_time = "24 h"  # Temps tampon pour récupérer les données nécessaires à l'interpolation.

[IWLS.API.Profile]
active = "public"  # Profil actif : {"dev", "prod", "public"}.

[IWLS.API.Environment.dev]
name = "DEV"
endpoint = "EndpointPrivateDev"
calls = 15  # Nombre maximal d'appels par période.
period = 1  # Période (en secondes).

[IWLS.API.Environment.prod]
name = "PROD"
endpoint = "EndpointPrivateProd"
calls = 10
period = 1

[IWLS.API.Environment.public]
name = "PUBLIC"
endpoint = "EndpointPublic"
calls = 15
period = 1

[IWLS.API.Cache]
ttl = 86400  # Durée de vie des données en cache (en secondes).
cache_path = "./cache"  # Répertoire pour le stockage du cache.

[DATA.Transformation.filter]
min_latitude = -90
max_latitude = 90
min_longitude = -180
max_longitude = 180
min_depth = 0
# max_depth = 1000 # Valeur maximale de profondeur (désactivée par défaut).

[DATA.Georeference.water_level]
water_level_tolerance = "15 min"  # Tolérance en pour le géoréférencement des niveaux d'eau.

[CSB.Processing.vessel]
manager_type = "VesselConfigJsonManager"
json_config_path = "./TCSB_VESSELSLIST.json"  # Chemin vers le fichier de configuration des navires.

[CSB.Processing.options]
log_level = "INFO"  # Niveau de log : {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}.
max_iterations = 10  # Nombre maximal d'itérations {int}.
export_format = ["gpkg", "csv"]  # Formats de fichier pour l'exportation des données traitées.
decimal_precision = 1  # Précision des décimales pour les données traitées.

[CARIS.Environment]
base_path = "C:/Program Files/CARIS"  # Chemin d'installation des logiciels CARIS.
software = "BASE Editor"  # Logiciel CARIS utilisé.
version = "5.5"  # Version spécifique du logiciel CARIS.
python_version = "3.11"  # Version de Python utilisée par l'API CARIS.
```

### Sections principales

- `[IWLS.API.TimeSeries]` (Optionnel) : Paramètres pour les séries temporelles. Si aucun paramètre n'est défini, les valeurs par défaut seront utilisées et aucune interpolation ne sera effectuée.
  - `priority` : Liste des séries temporelles à utiliser selon leur priorité (ex. : [`"wlo"`, `"wlp"`]).
  - `max_time_gap` : Temps maximal sans données avant interpolation (format : `"<nombre> <unité>"`, ex. : `"1 min"`).
  - `threshold_interpolation_filling` : Seuil pour l'interpolation et le remplissage des données manquantes (ex. : `"4 h"`).
  - `wlo_qc_flag_filter` : Filtres de qualité pour les données WLO.
  - `buffer_time` : Temps tampon pour les interpolations. (format : `"<nombre> <unité>"`, ex. : `"24 h"`).
- `[IWLS.API.Profile]` (Optionnel) : Définit le profil actif (`"dev"`, `"prod"`, `"public"`). Un profil public est utilisé par défaut avec 15 appels par seconde.
- `[IWLS.API.Environment.<profil>]` (Optionnel) : Paramètres spécifiques aux environnements
  - `name` : Nom de l'environnement (ex. : `"PUBLIC"`).
  - `endpoint` : Point de terminaison de l'API `"EndpointPublic"`). À noter, seulement les points de terminaison publics sont accessibles à tous.
  - `calls` : Nombre maximal d'appels par période.
  - `period` : Période de temps pour les appels.
- `[IWLS.API.Cache]` (Optionnel) : Définit la gestion du cache.
  - `ttl` : Durée de vie des données en cache (en secondes).
  - `cache_path` : Répertoire pour le stockage du cache.
- `[DATA.Transformation.filter]` (Optionnel) : Définit les limites géographiques et de profondeur pour filtrer les données.
- `[DATA.Georeference.water_level]` (Optionnel) : Définit la tolérance pour le géoréférencement basé sur les niveaux d'eau. (format : `"<nombre> <unité>"`, ex. : `"15 min"`).
- `[CSB.Processing.vessel]` (Optionnel) : Configure le gestionnaire et le fichier des navires. Obligatoire seulement si vous utilisez des navires pour le géoréférencement.
  - `manager_type` : Type de gestionnaire de navires (ex. : `"VesselConfigJsonManager"`).
  - `json_config_path` (Utilisé avec `"VesselConfigJsonManager"`) : Chemin vers le fichier de configuration des navires.
- `[CSB.Processing.options]` (Optionnel) : Options de traitement. 
  - `log_level` : Niveau de journalisation : {`"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`}.
  - `max_iterations` : Nombre maximal d'itérations.
  - `export_format` : Liste des formats de fichier pour l'exportation des données traitées : {`"geojson"`, `"gpkg"`, `"csar"`, `"parquet"`, `"feather"`, `"csv"`} (ex. : [`"gpkg"`, `"csv"`]).
  - `decimal_precision` : Nombre de décimales significatives pour les données traitées.
- `[CARIS.Environment]` (Optionnel) : Paramètres spécifiques à l'environnement CARIS. Sert à exporter les données au format CSAR.
  - `base_path` : Chemin d'installation des logiciels CARIS (par défaut : `"C:/Program Files/CARIS"`).
  - `software` : Logiciel CARIS utilisé (ex. : `"BASE Editor"`, `"HIPS and SIPS"`).
  - `version` : Version spécifique du logiciel CARIS (ex. : `"5.5"`).
  - `python_version` : Version de Python utilisée par l'API CARIS (ex. : `"3.11"`).
---

## Fichier des navires (Vessels)

Le fichier de configuration des navires est un fichier JSON contenant les informations nécessaires pour chaque navire, telles que 
l'identifiant, les conventions d'axes, et les données associées. Le chemin du fichier JSON est défini dans le fichier 
de configuration TOML. Voici un exemple de fichier :

```json
[
  {
    "id": "42134324",
    "name": "Tuktoyaktuk",
    "axis_convention": "CARIS",
    "navigation": [
      {
        "time_stamp": "2021-09-25T00:00:00Z",
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      },
      {
        "time_stamp": "2024-11-11T00:00:00Z",
        "x": 0.4,
        "y": 0.0,
        "z": 0.0
      }
    ],
    "motion": [
      {
        "time_stamp": "2021-09-25T00:00:00Z",
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      }
    ],
    "sounder": [
      {
        "time_stamp": "2021-09-25T00:00:00Z",
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      }
    ],
    "waterline": [
      {
        "time_stamp": "2021-09-25T00:00:00Z",
        "z": 0.0
      },
      {
        "time_stamp": "2024-11-11T00:00:00Z",
        "z": -0.65
      }
    ],
    "ssp_applied": [
      {
        "time_stamp": "2021-09-25T00:00:00Z",
        "ssp": false,
        "sound_speed": 1500.0
      }
    ]
  }
]
```

### Description des champs

- **`id`** : Identifiant unique du navire.
- **`name`** : Nom du navire.
- **`axis_convention`** : Convention d'axes utilisée (ex. : "CARIS").
- **`navigation`** : Liste des positions de navigation avec leurs coordonnées (`x`, `y`, `z`) et un horodatage (`time_stamp`).
- **`motion`** : Données de mouvement du navire (mêmes champs que `navigation`).
- **`sounder`** : Données du sondeur du navire (mêmes champs que `navigation`).
- **`waterline`** : Informations sur la ligne d'eau, incluant l'élévation (`z`) et un horodatage.
- **`ssp_applied`** : Indique si le modèle de propagation du son a été appliqué (`ssp`).

Pour tous les attributs `time_stamp`, le format doit être ISO 8601 (ex. : `"2021-09-25T00:00:00Z"`). De plus, le `time_stamp` 
indique la date à partir de laquelle la configuration est valide.

---

## Gestion des erreurs

Le module inclut une gestion robuste des erreurs pour éviter les interruptions inattendues. Voici les principaux cas pris en charge :

### Fichiers invalides
- **Problème** : Si un fichier fourni n'est pas valide (format incorrect ou inexistant).
- **Solution** : Le script journalise une erreur et ignore les fichiers non valides.
  ```bash
  [ERROR] Aucun fichier valide à traiter.
  ```

### Paramètres manquants
- **Problème** : Si un paramètre obligatoire comme `--output` est omis ou qu'il n'y a pas de fichiers à traiter.
- **Solution** : Le script affiche un message d'erreur expliquant le paramètre manquant.
  ```bash
  [ERROR] Le paramètre --output est obligatoire.
  ```
---

## Exemple d'utilisation complet

### Commande
```bash
python cli.py /data/fichier1.csv /data/dossier --output /data/output --vessel NAVIRE123 --config /config/config.toml --apply-water-level True
```

### Étapes détaillées
1. **Préparer les fichiers** : Assurez-vous que les fichiers sont au format pris en charge (`.csv`, `.txt`, `.xyz`).
2. **Créer une configuration** : Modifiez un fichier TOML pour définir vos paramètres spécifiques.
3. **Exécuter la commande** : Fournissez les chemins des fichiers, le répertoire de sortie, et d'autres options comme l'identifiant du navire.
4. **Vérifier les résultats** : Consultez le répertoire de sortie pour les fichiers traités et les journaux pour toute erreur ou avertissement.

---