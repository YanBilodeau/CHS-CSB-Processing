# Table of Contents

- [CHS-CSB-Processing](#chs-csb-processing)
- [Command-Line Interface Tutorial for Bathymetric File Processing](#command-line-interface-tutorial-for-bathymetric-file-processing)
  - [Description](#description)
  - [Main Command](#main-command)
    - [Available Options](#available-options)
      - [`files`](#files)
      - [`--output`](#--output)
      - [`--vessel`](#--vessel)
      - [`--config`](#--config)
  - [Configuration File (TOML)](#configuration-file-toml)
    - [Main Sections](#main-sections)
  - [Vessel File (Vessels)](#vessel-file-vessels)
    - [Field Descriptions](#field-descriptions)
  - [Error Handling](#error-handling)
    - [Invalid Files](#invalid-files)
    - [Missing Parameters](#missing-parameters)
  - [Complete Usage Example](#complete-usage-example)
    - [Command](#command)
    - [Detailed Steps](#detailed-steps)

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