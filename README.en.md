# Table of Contents

- [CHS-CSB-Processing](#chs-csb-processing)
- [Command-Line Interface Tutorial for Bathymetric File Processing](#command-line-interface-tutorial-for-bathymetric-file-processing)
  - [Description](#description)
  - [Main Command](#main-command)
    - [Available Options](#available-options)
      - [`files`](#files)
      - [`--output`](#--output)
      - [`--vessel`](#--vessel)
      - [`--waterline`](#--waterline)
      - [`--config`](#--config)
      - [`--apply-water-level`](#--apply-water-level)
  - [Processing Flow Diagram](#processing-flow-diagram)
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
- Identify and load appropriate files (CSV, TXT, XYZ, GeoJSON).
- Perform georeferencing based on specific configurations.
- Manage vessel identifiers and associated configurations.

The supported file formats are as follows:
- OFM: `.xyz` extension with at least the columns `LON`, `LAT`, `DEPTH`, `TIME` in the header.
- DCDB: `.csv` extension with at least the columns `LON`, `LAT`, `DEPTH`, `TIME` in the header.
- Lowrance: `.csv` extension with at least the columns `Longitude[°WGS84]`, `Latitude[°WGS84]`, `WaterDepth[Feet]`, 
            `DateTime[UTC]` in the header. These files are the result of `SL3` files from Lowrance exported by 
            the tool [SL3Reader](https://github.com/halmaia/SL3Reader).
- Actisense: coming soon.
- BlackBox: `.TXT` extension without header with columns in the order `Time`, `Date`, `Latitude`, `Longitude`, `Speed (km/h)` and `Depth (m)`.
- [WIBL](https://github.com/CCOMJHC/WIBL/tree/main): numeric extension (e.g., `.1`, `.2`, `.3`, etc.).

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

#### `--waterline`
- **Description**: Specifies the distance between the sounder and the waterline.
- **Type**: `float`
- **Required**: No
- **Details**: If this parameter is omitted, a waterline of 0 will be used.
- **Example**:
  ```bash
  python cli.py /data/file1.csv --waterline 1.4

#### `--config`
- **Description**: Specifies the path to the configuration file (TOML format).
- **Type**: `Path`
- **Required**: No
- **Details**: If this parameter is omitted, a default configuration file will be used.
- **Example**:
  ```bash
  python cli.py /data/file1.csv --config /config/config.toml
  ```

#### `--apply-water-level`
- **Description**: Enables or disables the reduction of water levels to chart datum during georeferencing.
- **Type**: `bool`
- **Required**: No
- **Details**: If this parameter is omitted, georeferencing based on water levels will be applied.
- **Example**:
  ```bash
  python cli.py /data/file1.csv --apply-water-level True

---

## Processing Flow Diagram

```mermaid
flowchart TD
    %% Global styles for the diagram
    classDef start fill:#66FF66,stroke:#009900,stroke-width:2px,color:#000000,font-weight:bold
    classDef process fill:#B9E0FF,stroke:#0078D7,stroke-width:1px,color:#000000
    classDef decision fill:#FFD700,stroke:#B8860B,stroke-width:1px,color:#000000
    classDef endNode fill:#FFA500,stroke:#FF4500,stroke-width:2px,color:#000000,font-weight:bold
    classDef highlighted fill:#CCEBFF,stroke:#0078D7,stroke-width:1px,color:#000000,font-weight:bold
    classDef iteration fill:#FF9ED2,stroke:#E63F8B,stroke-width:1px,color:#000000
    classDef export fill:#CCFFCC,stroke:#009900,stroke-width:1px,color:#000000

    %% Diagram nodes
    Start[Begin CSB workflow] --> Config[Loading configurations]
    Config --> CarisConfig{CSAR format required ?}
    CarisConfig -->|Yes| LoadCarisAPI[Loading Caris API configuration]
    CarisConfig -->|No| VesselConfig["<b>Loading vessel manager</b>
    • Retrieving vessel configuration"]
    LoadCarisAPI --> VesselConfig

    VesselConfig --> ParseFiles["<b>Parsing raw files:</b>
    • Format identification
    • Data reading
    • Conversion to GeoDataFrame
    • Pre-filtering of data"]
    ParseFiles --> CleanData["<b>Data cleaning and filtering:</b>
    • Duplicate removal
    • Min/max depth filtering
    • Invalid coordinate filtering
    • Invalid timestamp filtering
    • Min/max speed filtering"]
    CleanData --> CheckData{Valid data ?}
    CheckData -->|No| EndNoData[End: no valid data]
    CheckData -->|Yes| Outliers[Outlier detection]
    Outliers --> GetSensors[Retrieving sensor configurations based on vessel]

    GetSensors --> ApplyWL{Apply water level ?}
    ApplyWL -->|No| GeoreferenceNoWL["<b>Georeferencing without water level:</b>
    • TVU calculation
    • THU calculation
    • Survey order calculation"]
    GeoreferenceNoWL --> ExportNoWL[Exporting data & metadata]
    ExportNoWL --> EndNoWL[End: georeferenced data without water level]

    ApplyWL -->|Yes| LoadIWLS[Loading IWLS API configuration]
    LoadIWLS --> RunIter["run = 1, excluded_stations = (empty)"]

    RunIter --> IterCheck{run <= max_iterations ?}
    IterCheck -->|No| EndMaxRun[Incomplete processing: max iterations reached]
    EndMaxRun --> PlotWL
    %% EndMaxRun --> PlotWLMax[Creating available water level charts]
    %% PlotWLMax --> ExportDataMax[Exporting partially processed data]
    %% ExportDataMax --> ExportMetadataMax[Exporting metadata]
    %% ExportMetadataMax --> EndMaxComplete[End: export of available data]

    IterCheck -->|Yes| GetVoronoi["Retrieving tidal zones (Voronoi)
    without excluded stations"]
    GetVoronoi --> GetTideInfo[Retrieving tidal zone information
    intersecting with data]

    GetTideInfo --> GetWaterLevel[Retrieving water level data
    for each station]
    GetWaterLevel --> ExportWL[Exporting water level data]
    ExportWL --> Georeference["<b>Georeferencing bathymetric data:</b>
    • Applying water levels
    • TVU calculation
    • THU calculation
    • Survey order calculation"]

    Georeference --> DataComplete{Processing completed ?
    DEPTH_PROCESSED_METER without NaN ?}
    DataComplete -->|Yes| PlotWL[Creating water level charts]

    DataComplete -->|No| AddExcluded[Adding problematic stations
    to exclude]
    AddExcluded --> Increment[run += 1]
    Increment --> IterCheck

    PlotWL --> ExportData[Exporting processed data]
    ExportData --> ExportMetadata[Exporting metadata]
    ExportMetadata --> End[End: georeferenced data with water level]

    %% Applying styles to nodes
    class Start start
    class Config,LoadCarisAPI,VesselConfig,GetSensors,LoadIWLS process
    class CarisConfig,ApplyWL,IterCheck,DataComplete,CheckData decision
    class EndNoData,EndNoWL,EndMaxRun,EndMaxComplete,End endNode
    class ParseFiles,CleanData,GeoreferenceNoWL,Georeference highlighted
    class RunIter,GetVoronoi,GetTideInfo,GetWaterLevel,AddExcluded,Increment iteration
    class ExportNoWL,ExportWL,PlotWL,PlotWLMax,ExportData,ExportDataMax,ExportMetadata,ExportMetadataMax export
    class Outliers process
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
# min_speed = 0
# max_speed = 30
min_depth = 0
# max_depth = 1000 # Maximum depth value (disabled by default).
filter_to_apply = [
  "LATITUDE_FILTER",
  "LONGITUDE_FILTER",
  "TIME_FILTER",
  "SPEED_FILTER",
  "DEPTH_FILTER"
]

[DATA.Georeference.water_level]
water_level_tolerance = "15 min"  # Tolerance for georeferencing water levels.

[CSB.Processing.vessel]
manager_type = "VesselConfigJsonManager"
json_config_path = "./TCSB_VESSELSLIST.json"  # Path to vessel configuration file.

[CSB.Processing.options]
log_level = "INFO"  # Log level: {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}.
max_iterations = 5  # Maximum number of iterations {int}.
export_format = ["gpkg", "csv"]  # Formats of files for exporting processed data.
decimal_precision = 1  # Decimal precision for processed data.
group_by_iho_order = false  # Group data by IHO order.

[CARIS.Environment]
base_path = "C:/Program Files/CARIS"  # Path to the CARIS installation directory.
software = "BASE Editor"  # CARIS software to use.
version = "5.5"  # CARIS software version.   
python_version = "3.11"  # Python version to use.  
args = []  # Additional arguments for exporting data in CSAR format.
```

### Main Sections

- `[IWLS.API.TimeSeries]` (Optional): Parameters for time series. If no parameter is defined, default values will be used and no interpolation will be performed.
  - `priority`: List of time series to use by priority (e.g., `"wlo"`, `"wlp"`).
  - `max_time_gap`: Maximum time without data before interpolation (format: `"<number> <unit>"`, e.g., `"1 min"`).
  - `threshold_interpolation_filling`: Threshold for interpolation and filling missing data (e.g., `"4 h"`).
  - `wlo_qc_flag_filter`: Quality filters for WLO data.
  - `buffer_time`: Buffer time for interpolations (format: `"<number> <unit>"`, e.g., `"24 h"`).
- `[IWLS.API.Profile]` (Optional): Defines the active profile (`"dev"`, `"prod"`, `"public"`). A public profile is used by default with 15 calls per second.
- `[IWLS.API.Environment.<profile>]` (Optional): Environment-specific parameters
  - `name`: Name of the environment (e.g., `"PUBLIC"`).
  - `endpoint`: API endpoint (e.g., `"EndpointPublic"`). Note that only public endpoints are accessible to everyone.
  - `calls`: Maximum number of calls per period.
  - `period`: Time period for calls.
- `[IWLS.API.Cache]` (Optional): Defines cache management.
  - `ttl`: Cache data lifetime (in seconds).
  - `cache_path`: Directory for cache storage.
- `[DATA.Transformation.filter]` (Optional): Defines geographic, depth and speed limits for tagging inconsistent data.
  - `filter_to_apply`: List of filters to apply. Data is directly rejected if the filter is applied, otherwise data is simply tagged. Available filters are: `LATITUDE_FILTER` (Latitude filter), `LONGITUDE_FILTER` (Longitude filter), `TIME_FILTER` (Time filter), `SPEED_FILTER` (Speed filter), `DEPTH_FILTER`: Depth filter.
- `[DATA.Georeference.water_level]` (Optional): Defines tolerance for georeferencing based on water levels (format: `"<number> <unit>"`, e.g., `"15 min"`).
- `[CSB.Processing.vessel]` (Optional): Configures the vessel manager and vessel file. Required only if you use vessels for georeferencing.
  - `manager_type`: Type of vessel manager (e.g., `"VesselConfigJsonManager"`).
  - `json_config_path` (Used with `"VesselConfigJsonManager"`): Path to the vessel configuration file.
- `[CSB.Processing.options]` (Optional): Processing options.
  - `log_level` : Log level: {`"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`}.
  - `max_iterations` : Maximum number of iterations.
  - `export_format` : List of file formats for exporting processed data {`"geojson"`, `"gpkg"`, `"csar"`, `"parquet"`, `"feather"`, `"csv"`} (e.g. : [`"gpkg"`, `"csv"`]).
  - `decimal_precision` : Number of significant decimal places for processed data.
  - `group_by_iho_order` : Group data by IHO order.
- `[CARIS.Environment]` (Optional): CARIS environment-specific parameters. Used to export data in CSAR format.
  - `base_path`: Path to CARIS software installation (default: `"C:/Program Files/CARIS"`).
  - `software`: CARIS software used (e.g., `"BASE Editor"`, `"HIPS and SIPS"`).
  - `version`: Specific version of CARIS software (e.g., `"5.5"`).
  - `python_version`: Python version used by the CARIS API (e.g., `"3.11"`).
  - `args` : Additional arguments to pass for exporting data in CSAR format.

---

## Vessel File (Vessels)

The vessel configuration file is a JSON file containing the necessary information for each vessel, such as the 
identifier, axis conventions, and associated data. The path to the JSON file is defined in the TOML configuration file. 
Here is an example file:

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
    "sound_speed": [
      {
        "time_stamp": "2021-09-25T00:00:00Z",
        "ssp": false,
        "sound_speed": 1500.0
      }
    ]
  }
]
```

### Field Descriptions

- **`id`**: Unique vessel identifier.
- **`name`**: Vessel name.
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
python cli.py /data/file1.csv /data/folder --output /data/output --vessel VESSEL123 --config /config/config.toml --apply-water-level True
```

### Detailed Steps
1. **Prepare Files**: Ensure the files are in a supported format (`.csv`, `.txt`, `.xyz`).
2. **Create Configuration**: Modify a TOML file to define your specific parameters.
3. **Run Command**: Provide the file paths, output directory, and other options such as the vessel identifier.
4. **Verify Results**: Check the output directory for processed files and logs for any errors or warnings.

---
