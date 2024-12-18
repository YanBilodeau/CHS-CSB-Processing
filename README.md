# CHS-CSB-Processing

CHS-CSB-Processing est présentement en développement. Plusieurs fonctionnalités sont encore incomplètes ou en cours de développement.
Vous pouvez visiter la [documentation](https://chs-csb-processing.readthedocs.io/fr/latest/) pour plus d'informations.

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

#### `--config`
- **Description** : Spécifie le chemin du fichier de configuration (au format TOML).
- **Type** : `Path`
- **Obligatoire** : Non
- **Détails** : Si ce paramètre est omis, un fichier de configuration par défaut sera utilisé.
- **Exemple** :
  ```bash
  python cli.py /data/fichier1.csv --config /config/config.toml
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
```

### Sections principales

- `[IWLS.API.TimeSeries]` :
  - `priority` : Liste des séries temporelles à utiliser selon leur priorité (ex. : `"wlo"`, `"wlp"`).
  - `max_time_gap` : Temps maximal sans données avant interpolation (format : `"<nombre> <unité>"`, ex. : `"1 min"`).
  - `threshold_interpolation_filling` : Seuil pour l'interpolation et le remplissage des données manquantes (ex. : `"4 h"`).
  - `wlo_qc_flag_filter` : Filtres de qualité pour les données WLO.
  - `buffer_time` : Temps tampon pour les interpolations. (format : `"<nombre> <unité>"`, ex. : `"24 h"`).
- `[IWLS.API.Profile]` : Définit le profil actif (`"dev"`, `"prod"`, `"public"`).
- `[IWLS.API.Environment.<profil>]` : Paramètres spécifiques aux environnements (ex. : `endpoint`, `calls`, `period`).
- `[IWLS.API.Cache]` : Définit la gestion du cache (durée de vie et emplacement).
- `[DATA.Transformation.filter]` : Définit les limites géographiques et de profondeur pour filtrer les données.
- `[DATA.Georeference.water_level]` : Définit la tolérance pour le géoréférencement basé sur les niveaux d'eau. (format : `"<nombre> <unité>"`, ex. : `"15 min"`).
- `[CSB.Processing.vessel]` : Configure le gestionnaire et le fichier des navires.
- `[CSB.Processing.options]`
  - `log_level` : Niveau de journalisation : {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}.
  - `max_iterations` : Nombre maximal d'itérations {int}.

---

## Fichier des navires (Vessels)

Le fichier de configuration des navires est un fichier JSON contenant les informations nécessaires pour chaque navire, telles que 
l'identifiant, les conventions d'axes, et les données associées. Le chemin du fichier JSON est défini dans le fichier 
de configuration TOML. Voici un exemple de fichier :

```json
[
  {
    "id": "Tuktoyaktuk",
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
        "ssp": false
      }
    ]
  }
]
```

### Description des champs

- **`id`** : Identifiant unique du navire.
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
python cli.py /data/fichier1.csv /data/dossier --output /data/output --vessel NAVIRE123 --config /config/config.toml
```

### Étapes détaillées
1. **Préparer les fichiers** : Assurez-vous que les fichiers sont au format pris en charge (`.csv`, `.txt`, `.xyz`).
2. **Créer une configuration** : Modifiez un fichier TOML pour définir vos paramètres spécifiques.
3. **Exécuter la commande** : Fournissez les chemins des fichiers, le répertoire de sortie, et d'autres options comme l'identifiant du navire.
4. **Vérifier les résultats** : Consultez le répertoire de sortie pour les fichiers traités et les journaux pour toute erreur ou avertissement.

---

# CHS-CSB-Processing

CHS-CSB-Processing is currently under development. Several features are still incomplete or under development.
You can visit the [documentation](https://chs-csb-processing.readthedocs.io/en/latest/) for more information.

---
# Command-Line Interface Tutorial for Bathymetric File Processing

This tutorial provides a detailed explanation of how to use the command-line module to process and georeference 
bathymetric data files. It covers every parameter and provides practical examples.

---

## Description

This module is designed to automate the processing of bathymetric data files. It allows you to:
- Identify and load appropriate files (CSV, TXT, XYZ).
- Perform georeferencing based on specific configurations.
- Manage vessel identifiers and associated configurations.

The supported file formats are as follows:
- OFM: `.xyz` extension with at least the columns `LON`, `LAT`, `DEPTH`, `TIME` in the header.
- DCDB: `.csv` extension with at least the columns `LON`, `LAT`, `DEPTH`, `TIME` in the header.
- Lowrance: `.csv` extension with at least the columns `Longitude[°WGS84]`, `Latitude[°WGS84]`, `WaterDepth[Feet]`, 
            `DateTime[UTC]` in the header. These files are the result of `SL3` files from Lowrance exported by 
            the tool [SL3Reader](https://github.com/halmaia/SL3Reader).
- Actisense: coming soon.
- BlackBox: coming soon.

---

## Main Command

```bash
python cli.py <files> [options]
```

### Available Options

#### `files`
- **Description**: Specifies the paths of the files or directories to be processed.
- **Type**: `Collection[Path]`
- **Required**: Yes
- **Details**: You can provide one or multiple paths. If a directory is specified, all valid files it contains will be included.
- **Example**:
  ```bash
  python cli.py /data/file1.csv /data/folder
  ```

#### `--output`
- **Description**: Specifies the output directory for the processed files.
- **Type**: `Path`
- **Required**: Yes
- **Details**: If this parameter is not set, the script will not save the processed files.
- **Example**:
  ```bash
  python cli.py /data/file1.csv --output /data/output
  ```

#### `--vessel`
- **Description**: Provides the vessel identifier for processing.
- **Type**: `str`
- **Required**: No
- **Details**: If no identifier is provided, a default vessel with lever arms set to 0 will be used.
- **Example**:
  ```bash
  python cli.py /data/file1.csv --vessel VESSEL123
  ```

#### `--config`
- **Description**: Specifies the path to the configuration file (TOML format).
- **Type**: `Path`
- **Required**: No
- **Details**: If this parameter is omitted, a default configuration file will be used.
- **Example**:
  ```bash
  python cli.py /data/file1.csv --config /config/config.toml
  ```

---

## Configuration File (TOML)

The TOML configuration file defines parameters for processing. Below is an example of the default configuration file (./src/CONFIG_csb-processing.toml):

```toml
[IWLS.API.TimeSeries]
priority = ["wlo", "wlp"]  # Priority of time series to retrieve.
max_time_gap = "1 min"  # Maximum interval without data before interpolation.
threshold_interpolation_filling = "4 h"  # Threshold for interpolation and filling missing data.
wlo_qc_flag_filter = ["NOT_EVAL", "QUESTIONABLE", "BAD", "MISSING", "2", "3"]  # Quality filters for wlo.
buffer_time = "24 h"  # Buffer time to retrieve data needed for interpolation.

[IWLS.API.Profile]
active = "public"  # Active profile: {"dev", "prod", "public"}.

[IWLS.API.Environment.dev]
name = "DEV"
endpoint = "EndpointPrivateDev"
calls = 15  # Maximum number of calls per period.
period = 1  # Period (in seconds).

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
ttl = 86400  # Cache data lifetime (in seconds).
cache_path = "./cache"  # Directory for cache storage.

[DATA.Transformation.filter]
min_latitude = -90
max_latitude = 90
min_longitude = -180
max_longitude = 180
min_depth = 0
# max_depth = 1000 # Maximum depth value (disabled by default).

[DATA.Georeference.water_level]
water_level_tolerance = "15 min"  # Tolerance for georeferencing water levels.

[CSB.Processing.vessel]
manager_type = "VesselConfigJsonManager"
json_config_path = "./TCSB_VESSELSLIST.json"  # Path to vessel configuration file.

[CSB.Processing.options]
log_level = "INFO"  # Log level: {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}.
max_iterations = 10  # Maximum number of iterations {int}.
```

### Main Sections

- `[IWLS.API.TimeSeries]`:
  - `priority`: List of time series to use by priority (e.g., `"wlo"`, `"wlp"`).
  - `max_time_gap`: Maximum time without data before interpolation (format: `"<number> <unit>", e.g., "1 min"`).
  - `threshold_interpolation_filling`: Threshold for interpolation and filling missing data (e.g., `"4 h"`).
  - `wlo_qc_flag_filter`: Quality filters for WLO data.
  - `buffer_time`: Buffer time in hours for interpolations. (format: `"<number> <unit>", e.g., "24 h"`).
- `[IWLS.API.Profile]`: Defines the active profile (`"dev"`, `"prod"`, `"public"`).
- `[IWLS.API.Environment.<profile>]`: Environment-specific parameters (e.g., `endpoint`, `calls`, `period`).
- `[IWLS.API.Cache]`: Defines cache management (lifetime and location).
- `[DATA.Transformation.filter]`: Sets geographic and depth limits for filtering data.
- `[DATA.Georeference.water_level]`: Defines tolerance for georeferencing based on water levels (format: `"<number> <unit>", e.g., "15 min"`).
- `[CSB.Processing.vessel]`: Configures the vessel manager and vessel file.
- `[CSB.Processing.options]`
  - `log_level`: Log level: {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}.
  - `max_iterations`: Maximum number of iterations {int}.

---

## Vessel File (Vessels)

The vessel configuration file is a JSON file containing the necessary information for each vessel, such as the 
identifier, axis conventions, and associated data. The path to the JSON file is defined in the TOML configuration file. 
Here is an example file:

```json
[
  {
    "id": "Tuktoyaktuk",
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
        "ssp": false
      }
    ]
  }
]
```

### Field Descriptions

- **`id`**: Unique vessel identifier.
- **`axis_convention`**: Axis convention used (e.g., "CARIS").
- **`navigation`**: List of navigation positions with their coordinates (`x`, `y`, `z`) and a timestamp (`time_stamp`).
- **`motion`**: Vessel motion data (same fields as `navigation`).
- **`sounder`**: Vessel sounder data (same fields as `navigation`).
- **`waterline`**: Waterline information, including elevation (`z`) and a timestamp.
- **`ssp_applied`**: Indicates whether the sound speed profile model has been applied (`ssp`).

For all `time_stamp` attributes, the format must be ISO 8601 (e.g., `"2021-09-25T00:00:00Z"`). Additionally, the 
`time_stamp` indicates the date from which the configuration is valid.

---

## Error Handling

The module includes robust error handling to avoid unexpected interruptions. Below are the main cases covered:

### Invalid Files
- **Issue**: If a provided file is invalid (incorrect format or non-existent).
- **Solution**: The script logs an error and skips invalid files.
  ```bash
  [ERROR] No valid files to process.
  ```

### Missing Parameters
- **Issue**: If a required parameter such as `--output` is missing.
- **Solution**: The script displays an error message explaining the missing parameter.
  ```bash
  [ERROR] The --output parameter is required.
  ```
---

## Complete Usage Example

### Command
```bash
python cli.py /data/file1.csv /data/folder --output /data/output --vessel VESSEL123 --config /config/config.toml
```

### Detailed Steps
1. **Prepare Files**: Ensure the files are in a supported format (`.csv`, `.txt`, `.xyz`).
2. **Create Configuration**: Modify a TOML file to define your specific parameters.
3. **Run Command**: Provide the file paths, output directory, and other options such as the vessel identifier.
4. **Verify Results**: Check the output directory for processed files and logs for any errors or warnings.

---
