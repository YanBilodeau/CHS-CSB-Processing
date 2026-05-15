# GitHub Copilot Instructions — CHS-CSB_Processing

Python pipeline for the **Canadian Hydrographic Service (CHS / SHC)** — Crowdsourced Bathymetry (CSB) data
processing: ingestion, cleaning, georeferencing, water-level reduction (IWLS), and multi-format export.
**Python 3.11**, Windows environment. CARIS BASE Editor 6.1 is an **optional** dependency (CSAR export only).

___

## Language & Style

- **Docstrings must be in French.** All other code (comments, variable names, UI labels, log messages) must be in *
  *English**.
- Exception messages may be in English.

### Docstring Style — Sphinx / reStructuredText

Always use the **Sphinx/reStructuredText** format for all docstrings. Never use Google style or NumPy style.

```python
def my_function(param1: str, param2: Path) -> list[str]:
    """
    Description courte de la fonction en français.

    Description longue optionnelle si nécessaire.

    :param param1: Description du premier paramètre.
    :type param1: str
    :param param2: Description du second paramètre.
    :type param2: Path
    :return: Description de la valeur retournée.
    :rtype: list[str]
    :raises ValueError: Si param1 est vide.
    """
```

Rules:

- **One-line docstrings** are allowed for trivial functions (no params/return needed).
- **Multi-line docstrings**: opening `"""` on the first line with the short description, closing `"""` on its own line.
- Always document **all parameters** (`:param:` + `:type:`), the **return value** (`:return:` + `:rtype:`), and **raised
  exceptions** (`:raises:`).
- Use `None` as `:rtype:` when the function returns nothing meaningful.
- For `Optional[X]` return types, use `:rtype: X | None`.
- Windows paths always use `\\` (raw strings or double backslash). Prefer **`pathlib.Path`** over `os.path` for all path
  manipulation.
- Use **Pydantic** for all config/data model validation.
- Use **loguru** for logging (see Logging section). Do NOT mix with `verboselogs`/`coloredlogs` in the same module.
- Prefer **type hints** on all function signatures.

---

## Module Architecture

The project is a single Python package rooted at `src/`. All business logic lives in focused sub-packages under `src/`.

```
src/
  cli.py                      # Click CLI entrypoint (process / convert commands)
  web_ui.py                   # NiceGUI web UI entrypoint
  csb_processing.py           # Canonical end-to-end workflow (processing_workflow)
  converter.py                # Standalone GPKG/GeoJSON → format conversion
  iwls_api.py                 # IWLS API initialization facade
  processing_context.py       # ProcessingContext dataclass (shared per-run state)
  CONFIG_csb-processing.toml  # Executable defaults — the source of truth for options
  CONFIG_vessels.json         # Default vessel configuration
  config/                     # Pydantic config models + TOML loader
  ingestion/                  # Raw file parsers (factory + ABC + format implementations)
  filter/                     # Data cleaning and filtering
  transformation/             # Georeferencing and uncertainty computation
  tide/                       # Voronoi, tide zones, time series, water level export
  export/                     # Multi-format export (GPKG, GeoJSON, CSV, Parquet, CSAR…)
  metadata/                   # Metadata models, HTML/PDF report generation
  vessel/                     # Vessel configuration management (JSON, SQLite, factory)
  schema/                     # Pandera schemas (DataLoggerSchema, TideZoneStationSchema…)
  logger/                     # loguru configuration (configure_logger, routing)
  app/                        # NiceGUI web UI components and handlers
  iwls_api_request/           # IWLS HTTP client (private/public API, rate limiter, cache)
  caris_api/                  # Optional CARIS integration (CSAR export — pyapi + batch)
  static/                     # Static assets (icons, images)
```

**Output structure** (fixed by `export.get_data_structure(...)`):

```
<output>/
  Data/    ← processed sounding files (GPKG, GeoJSON, CSAR…) + metadata (HTML, JSON, PDF)
  Tide/    ← water level CSVs, Voronoi GPKG, WaterLevel.html plot
  Log/     ← CHS-CSB-Processing.log (rotating, loguru)
```

---

## Design Principles

### SOLID

- **S — Single Responsibility:** every class and module has one reason to change. Split large modules into focused
  sub-modules.
- **O — Open/Closed:** extend behaviour via subclassing or strategy injection, not by modifying existing code.
- **L — Liskov Substitution:** subtypes must be substitutable for their base types; use `Protocol` to define contracts.
- **I — Interface Segregation:** prefer small, focused `Protocol` interfaces over large abstract base classes.
- **D — Dependency Inversion:** depend on abstractions (`Protocol`), not concrete implementations. Inject dependencies
  through constructors or factory functions.

### Code Quality

- **Short functions:** each function does one thing and fits on a screen (~20–30 lines max). Extract helpers rather than
  nesting logic.
- **High cohesion:** group code that changes together. A module should have a clear, single purpose.
- **Low coupling:** use `Protocol` and dependency injection to decouple components. Avoid importing concrete classes
  across module boundaries when a protocol suffices.

```python
# Prefer Protocol + injection over direct import of concrete class
from typing import Protocol


class StorageBackend(Protocol):
    def upload(self, local_path: Path, remote_path: str) -> None: ...


class DataExporter:
    def __init__(self, storage: StorageBackend) -> None:
        self._storage = storage

    def export(self, path: Path) -> None:
        self._storage.upload(path, path.name)
```

### Functional Paradigm

- **Prefer functional style** when there is no need to maintain state: pure functions, `map`, `filter`, list/dict
  comprehensions, `itertools`.
- Avoid side effects in transformation functions; return new values instead of mutating inputs.
- Reserve classes for cases where state or behaviour grouping is genuinely needed.

```python
# Prefer this...
depths_valid = [d for d in depths if d > 0]
total = sum(d * scale for d in depths_valid)

# ...over mutating a list in-place inside a loop
```

### Generators and Lazy Evaluation

- **Prefer generators over lists** whenever the full sequence is not needed at once: use `yield` / `yield from`,
  generator expressions `(x for x in ...)`, and `itertools` lazy combinators.
- Generators reduce peak memory usage and enable early exit — especially valuable for large HIPS datasets, file
  iteration, or pipeline stages that filter most items.
- Use `yield from` to delegate to sub-iterables cleanly.

```python
# ✅ Generator — lazy, memory-efficient
def iter_valid_lines(per_line: dict) -> Generator[str, None, None]:
    """Itère sur les lignes non ignorées."""
    yield from (name for name, s in per_line.items() if not s.get("skipped", False))


# ❌ List — builds entire sequence in memory before first use
def get_valid_lines(per_line: dict) -> list[str]:
    return [name for name, s in per_line.items() if not s.get("skipped", False)]
```

- Annotate generator return types with `Generator[YieldType, SendType, ReturnType]` from `collections.abc`, or the
  shorthand `Iterator[YieldType]` when send/return are unused.
- **Do not** use generators when random access, `len()`, or multiple passes are required — convert to `list` explicitly
  at the call site.
- For async pipelines (use `AsyncGenerator` / `async for` instead of blocking generators.

### Vectorized Operations

- **Always prefer vectorized operations** over explicit Python loops when working with **NumPy**, **pandas**,
  **GeoPandas**, or **Polars**.
- Use built-in array/Series/DataFrame methods (`.apply()` only as a last resort) instead of iterating row-by-row.
- Prefer boolean indexing, `.loc[]`, `.query()`, and vectorized arithmetic over `for` / `while` loops.
- For GeoPandas, use vectorized spatial operations (`sjoin`, `overlay`, `buffer`, `unary_union`) instead of per-feature
  loops.
- For Polars, prefer expressions (`.filter()`, `.with_columns()`, `.select()`) over `.apply()` or `.map_elements()`.

```python
# ✅ Vectorized — fast
mask = df["depth"] > 0
mean_depth = df.loc[mask, "depth"].mean()

# ❌ Loop — slow, avoid
total = 0
for _, row in df.iterrows():
    if row["depth"] > 0:
        total += row["depth"]
```

### Dataclasses for Cohesive Data

- Use **`@dataclass`** (or **`@dataclass(frozen=True)`** for immutable value objects) to group tightly related data
  fields.
- Prefer `dataclass` over plain `dict` or `tuple` whenever the data has a clear semantic identity.
- Use **Pydantic `BaseModel`** instead when external validation or serialization (JSON, TOML) is required.

```python
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SwathInfo:
    """Informations d'une portée HIPS."""
    name: str
    hips_file: Path
    vessel_code: str
    line_numbers: list[int] = field(default_factory=list)
```

---

## Application Sub-packages (`src/`)

| Sub-package         | Role                                                                                                                                                         |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `cli.py`            | Click CLI — `process` and `convert` commands; file validation and workflow dispatch                                                                          |
| `web_ui.py`         | NiceGUI web interface — mirrors CLI behaviour through `app/processing_handler.py`                                                                            |
| `csb_processing.py` | Core orchestration — `processing_workflow()` (parse → clean → georeference → export)                                                                         |
| `converter.py`      | Standalone conversion of processed GPKG/GeoJSON to other formats                                                                                             |
| `config/`           | Pydantic config models (`CSBprocessingConfig`, `CarisAPIConfig`, `IWLSConfig`); TOML loader with `@lru_cache`                                                |
| `ingestion/`        | Factory-based raw data parsers (DCDB, BlackBox, Lowrance, OFM, B12-CSB, WIBL, HydroBlock)                                                                    |
| `filter/`           | Data cleaning, speed/depth/position/datetime filters, outlier detection                                                                                      |
| `transformation/`   | Georeferencing (`georeference_bathymetry`), uncertainty computation, IHO order                                                                               |
| `tide/`             | Voronoi diagram, tide-zone join, IWLS time series fetch/interpolation, water level plot                                                                      |
| `export/`           | Multi-format export factory (GPKG, GeoJSON, CSV, Parquet, Feather, GeoTIFF, CSAR)                                                                            |
| `metadata/`         | Metadata models, HTML/PDF report generation                                                                                                                  |
| `vessel/`           | Vessel config: JSON manager, SQLite manager, factory, unknown vessel fallback                                                                                |
| `schema/`           | Pandera schemas (`DataLoggerSchema`, `DataLoggerWithTideZoneSchema`, `TideZoneStationSchema`, `WaterLevelSerieDataWithMetaDataSchema`) + column ID constants |
| `logger/`           | loguru `configure_logger()`, log routing, logger IDs                                                                                                         |
| `app/`              | NiceGUI UI components: `ProcessingHandler`, `FileManager`, `ConfigManager`, `Validator`, `UIRunner`, and UI sections/components                              |
| `iwls_api_request/` | IWLS HTTP client — `get_iwls_api()` factory, private/public API, `RateLimiterHandler`, retry adapter, optional cache session                                 |
| `caris_api/`        | Optional CARIS integration — `export_csar_api` (Python API), `export_csar_batch` (CLI); guarded by runtime imports                                           |

---

## Configuration

**Main configuration file:** `src/CONFIG_csb-processing.toml`  
Treat it as executable documentation — all options with defaults are defined here.

**Access pattern — always use the cached loader:**

```python
from config.helper import load_config
from config import get_data_config, get_caris_api_config

processing_config = get_data_config(config_file=config_path)  # CSBprocessingConfig (Pydantic)
caris_api_config = get_caris_api_config(config_file=config_path)  # CarisAPIConfig (Pydantic)
```

`load_config()` in `src/config/helper.py` is decorated with `@lru_cache` — avoid side effects that depend on
re-reading TOML within the same process.

**Vessel configuration:** `src/CONFIG_vessels.json` — resolved by `src/vessel/vessel_config_json_manager.py`
(non-absolute paths resolved from `Path(__file__).parent.parent`).

**Key Pydantic models** (all in `src/config/processing_config.py`):

| Model                 | Purpose                                                |
|-----------------------|--------------------------------------------------------|
| `CSBprocessingConfig` | Top-level config (filter, export, georeference, …)     |
| `FileTypes`           | Output format enum (`gpkg`, `geojson`, `csar`, …)      |
| `Filter`              | Active filter enum (`SPEED_FILTER`, `DEPTH_FILTER`, …) |
| `CarisAPIConfig`      | CARIS BASE Editor paths (optional, CSAR only)          |

> Always use **`pathlib.Path`** for path construction and manipulation. Never use string concatenation or `os.path`.
>
> ```python
> from pathlib import Path
> config_path = Path(__file__).parent / "CONFIG_csb-processing.toml"
> output_data = output / "Data"
> ```

---

## Logging

Use **loguru** with a module-bound logger. Do NOT use `verboselogs`/`coloredlogs`.

```python
from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.MyModule")
LOGGER.info("Processing started")
```

**Logger name convention:** `CSB-Processing.<SubPackage>[.<Component>]`  
Examples: `CSB-Processing.WorkFlow`, `CSB-Processing.CLI`, `CSB-Processing.Export.Helpers`,
`CSB-Processing.Ingestion.Parser.Factory`, `IWLS.API.APIFacade`.

Initialize at application startup (called once in `csb_processing.py` and `cli.py`):

```python
from logger.loguru_config import configure_logger

configure_logger(
    log_file=log_path / "CHS-CSB-Processing.log",
    std_level=processing_config.options.log_level,
    log_file_level="DEBUG",
    extra_logger=extra_logger,  # optional NiceGUI log handler sink
)
```

`configure_logger()` signature (`src/logger/loguru_config.py`):

```python
def configure_logger(
        log_file: Optional[Path] = None,
        std_level: str = "INFO",
        log_file_level: str = "TRACE",
        rotation: str | int = "1 day",
        retention: str | int = "30 days",
        enqueue: bool = True,
        extra_logger: Optional[Iterable[dict]] = None,
) -> None: ...
```

---

## Key Patterns

### Strategy & Policy Pattern

Use the **Strategy** pattern to select an algorithm at runtime without `if/elif` chains.
Encode the dispatch table as a plain `dict` mapping an enum (or string key) to a callable.
A **Policy** is a strategy variant where the callable is a pure predicate or decision function
injected as a parameter — it decides *how* to behave, not *what* to compute.

```python
from typing import Protocol


class NamingStrategy(Protocol):
    def build_name(self, project: str, vessel: str) -> str: ...


_STRATEGIES: dict[Structure, NamingStrategy] = {
    Structure.CH: SeawayNaming(),
    Structure.LR: SurveyNaming(),
}


def get_coverage_name(structure: Structure, project: str, vessel: str) -> str:
    """Retourne le nom de couverture selon la stratégie de levé."""
    return _STRATEGIES[structure].build_name(project, vessel)
```

- Always back the dispatch table with a `Protocol` so each strategy is type-checked.
- Prefer a module-level `dict` over `match/case` when strategies are open to extension.
- Inject the strategy through the constructor or as a parameter — never hard-code the selection inside a method.

---

### Function Composition

Compose small, pure transformation functions instead of writing long imperative pipelines.
Use `functools.reduce` or a hand-rolled `compose`/`pipe` helper for sequential transforms.

```python
from collections.abc import Callable
from functools import reduce
from typing import TypeVar

T = TypeVar("T")


def pipe(*fns: Callable[[T], T]) -> Callable[[T], T]:
    """Compose plusieurs transformations en une seule fonction de gauche à droite."""
    return lambda x: reduce(lambda v, f: f(v), fns, x)


# Usage
process = pipe(
    filter_nodata,
    apply_depth_direction,
    clip_to_range,
)
clean_array = process(raw_array)
```

- Each stage must be a **pure function** (no side effects, returns a new value).
- Compose at the call site, not inside the stage functions — keeps stages independently testable.
- For async stages, use `AsyncGenerator` composition (see *Pipeline Pattern* below).

---

### Dependency Injection & Dependency Inversion

**Dependency Inversion** (DIP): high-level modules must not import low-level concrete classes.
Both must depend on an abstraction (`Protocol`).

**Dependency Injection** (DI): pass dependencies through constructors or factory parameters —
never instantiate collaborators inside a class.

```python
from typing import Protocol
from pathlib import Path


# Abstraction (port)
class DiffComputer(Protocol):
    def compute(self, coverage: Path, reference: Path) -> Path | None: ...


# High-level module depends only on the protocol
class GroundTruthPipeline:
    """Pipeline de comparaison ground truth."""

    def __init__(self, diff_computer: DiffComputer) -> None:
        self._diff_computer = diff_computer  # injected, not instantiated here

    def run(self, coverage: Path, reference: Path) -> GroundTruthResult | None:
        """Exécute la comparaison ground truth."""
        diff_file = self._diff_computer.compute(coverage, reference)
        ...


# Wiring lives in main.py / factory — not in the pipeline
pipeline = GroundTruthPipeline(diff_computer=CarisBatchDiffComputer())
```

- Inject via `__init__` for mandatory collaborators, via function parameter for optional ones.
- Never call `SomeConcreteClass()` inside a business-logic class — use a factory or pass it in.
- `Protocol` + `runtime_checkable` enables structural typing without inheritance.

---

### Clean Architecture — Ports & Adapters (Hexagonal)

Organise code in concentric layers: **domain → application → infrastructure**.
The domain and application layers must have **zero imports** from infrastructure (CARIS API, HTTP, DB).

```
schema/             ← pure Python models/protocols, no external deps (Pandera schemas, column IDs)
config/             ← application config (Pydantic models, TOML loader)
filter/ transformation/ tide/ export/ metadata/ vessel/  ← application logic
iwls_api_request/   ← infrastructure: HTTP client, rate limiter, cache
caris_api/          ← infrastructure: optional CARIS adapter (runtime imports only)
cli.py / web_ui.py  ← wiring only — entrypoints that assemble and call processing_workflow()
```

**Port** = a `Protocol` defined in `schema/` or a sub-package's `*_abc.py` / `*_models.py`.  
**Adapter** = a concrete class in `iwls_api_request/`, `caris_api/`, or `vessel/`.

```python
# vessel/vessel_config_manager_abc.py — port
class VesselConfigManagerABC(Protocol):
    def get_vessel_config(self, vessel_id: str) -> VesselConfig: ...


# vessel/vessel_config_json_manager.py — adapter
class VesselConfigJsonManager:
    """Gestionnaire de configuration de navires depuis un fichier JSON."""

    def get_vessel_config(self, vessel_id: str) -> VesselConfig: ...


# csb_processing.py — wiring
vessel_config = vessel_manager.get_vessel_config(vessel, processing_config.vessel_manager)
```

- Keep **runtime** CARIS imports inside `src/caris_api/` functions only — never at module level.
- Never let a `Protocol` import from `caris_api/` or `iwls_api_request/`.

---

### Command Pattern

Encapsulate a request as an object so it can be queued, logged, retried, or undone.
Used in `lib/hips_command_line_utilities/` for HIPS CLI commands.

```python
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


class Command(ABC):
    """Commande CLI abstraite."""

    @abstractmethod
    def to_args(self) -> list[str]:
        """Retourne la liste d'arguments pour subprocess."""
        ...


@dataclass(frozen=True)
class ExportSoundingsCommand(Command):
    """Commande d'export de sondages HIPS."""
    hips_file: Path
    output_dir: Path
    lines: list[str] = field(default_factory=list)

    def to_args(self) -> list[str]:
        """Retourne les arguments CLI pour HIPS Export."""
        args = ["hipsexport.exe", str(self.hips_file), "-o", str(self.output_dir)]
        args += [f"/line={l}" for l in self.lines]
        return args
```

- Commands are **immutable dataclasses** (`frozen=True`) — no state mutation after creation.
- The executor (`SubprocessSyncExecutor`, `AsyncSubprocessExecutor`) is separate from the command — respects SRP.
- For retries, wrap the executor call with `tenacity`, not the command itself.

---

### Pipeline Pattern — AsyncGenerator & Function Composition

Model multi-stage data pipelines as chains of `AsyncGenerator` functions.
Each stage consumes an `AsyncIterable` and yields transformed items — stages are composable
and memory-efficient (items flow one at a time).

```python
from collections.abc import AsyncGenerator, AsyncIterable

type Item = dict  # replace with your domain type


async def read_source(paths: list[Path]) -> AsyncGenerator[Item, None]:
    """Lit les fichiers source et émet des items bruts."""
    for path in paths:
        async for item in _parse_file(path):
            yield item


async def validate(source: AsyncIterable[Item]) -> AsyncGenerator[Item, None]:
    """Filtre les items invalides."""
    async for item in source:
        if _is_valid(item):
            yield item


async def enrich(source: AsyncIterable[Item]) -> AsyncGenerator[Item, None]:
    """Enrichit chaque item avec des métadonnées."""
    async for item in source:
        yield {**item, "metadata": await _fetch_metadata(item["id"])}


async def run_pipeline(paths: list[Path]) -> None:
    """Orchestre le pipeline complet."""
    pipeline = enrich(validate(read_source(paths)))
    async for result in pipeline:
        await _persist(result)
```

**Rules:**

- Each stage has **one responsibility** — filter, transform, or enrich.
- Stages must be **pure generators** (no side effects except the final sink).
- The **sink** (final `async for` loop) is the only place with side effects (persist, log, notify).

---

### Factory Pattern — Parser Selection

Parser selection is factory-based in `src/ingestion/factory_parser.py`.

```python
from ingestion import factory_parser

parser_files: factory_parser.ParserFiles = factory_parser.get_files_parser(files=files)
datalogger_type: DataLoggerType = parser_files.datalogger_type
data: gpd.GeoDataFrame = parser_files.parser.from_files(files=parser_files.files)
```

- **Extension normalization + header matching** determines the parser.
- `ParserFiles` enforces a **single parser type per run** — mixed formats raise `MultipleParsersError`.
- Register a new parser: add class in `src/ingestion/`, register in `FACTORY_PARSER` dict, map in `DATA_TYPE_MAPPING`.

```python
# ingestion/factory_parser.py
FACTORY_PARSER: dict[str, type[DataParserABC]] = {
    "dcdb": DataParserBCDB,
    "black_box": DataParserBlackBox,
    "lowrance": DataParserLowrance,
    "ofm": DataParserOFM,
    "b12_csb": DataParserB12CSB,
    "wibl": DataParserWIBL,
    "hydroblock": DataParserHydroBlock,
}
```

### Factory Pattern — Export Format Selection

Export format selection is factory-based in `src/export/factory_export.py`.

```python
from export.factory_export import export_geodataframe, FileTypes

export_geodataframe(
    geodataframe=data,
    output_path=export_data_path / file_name,
    file_type=FileTypes.GPKG,
    config=processing_config,
)
```

- Register a new format: implement `export_geodataframe_to_<fmt>(...)` in `src/export/export_format.py`,
  register in `FACTORY_EXPORT_GEODATAFRAME`, expose in `FileTypes` enum and CLI `--format` choices.

### Factory Pattern — Vessel Config Manager

```python
from vessel import factory_vessel_config_manager, VesselConfigManagerType

manager = factory_vessel_config_manager.get_vessel_config_manager(
    manager_type=VesselConfigManagerType.JSON,
    kwargs={"vessel_config_path": Path("CONFIG_vessels.json")},
)
vessel_config = manager.get_vessel_config(vessel_id="SHIP_ID")
```

### IWLS API — Factory + Rate-Limiter + Cache

```python
from iwls_api_request.api_facade import get_iwls_api, EnvironmentType, HandlerType
from iwls_api_request.api.endpoint import Endpoint
from iwls_api_request.handler.http_query_handler import CachedSessionConfig, SessionType

api = get_iwls_api(
    endpoint=Endpoint.PUBLIC,
    handler_type=HandlerType.RATE_LIMITER,
    calls=10,
    period=1,
    session_type_config=CachedSessionConfig(cache_path=Path("cache/cache.db")),
    retry_adapter_config=True,
)
```

- `EnvironmentType`: `DEV`, `PROD`, `PUBLIC`
- `HandlerType`: `RATE_LIMITER` (default), `REQUESTS`
- Session types: `SessionType.REQUESTS` (plain), `SessionType.CACHE` (requests-cache)

---

## GUI — NiceGUI Web Interface

The web UI (`src/web_ui.py`) uses **NiceGUI** and mirrors CLI behaviour through `src/app/processing_handler.py`.

```python
from app import (
    FileDisplay, FileManager, LogDisplay, UILogHandler, StatusDisplay,
    ThemeManager, Validator, UIRunner, FileSelectionComponentNative,
    OptionsComponent, HeaderComponent, ProcessingHandler, ConfigManager,
    FileOperations, UIEventHandler, ProcessingSection, StatusSection, LogSection,
)
```

**Key components** (`src/app/`):

| Module                  | Role                                                                                  |
|-------------------------|---------------------------------------------------------------------------------------|
| `processing_handler.py` | `ProcessingHandler.process_files()` — calls `processing_workflow()` in asyncio thread |
| `config_manager.py`     | `ConfigManager` — reads/writes TOML config from the UI                                |
| `file_manager.py`       | `FileManager` — manages the list of input files                                       |
| `file_operations.py`    | `FileOperations` — drag-and-drop, file dialog helpers                                 |
| `log_handler.py`        | `UILogHandler` — loguru sink that streams log messages to the UI                      |
| `ui_validation.py`      | `Validator` — validates vessel/waterline/config UI inputs                             |
| `runner.py`             | `UIRunner` — async task runner that bridges NiceGUI event loop                        |
| `ui_events.py`          | `UIEventHandler` — wires NiceGUI events to handlers                                   |
| `network_helper.py`     | Network utility helpers (port availability…)                                          |
| `component/`            | Reusable NiceGUI component classes (log display, status, file display…)               |

**CLI / UI parity rule:** file filtering logic (`is_valid_file` / `get_files`) is duplicated in
`src/cli.py` and `src/app/processing_handler.py` — **keep both in sync** when changing file acceptance rules.

**Launch:**

```powershell
python src/web_ui.py        # or
.\run_WebUI.bat
```

---

## Key Sub-package Details

### `src/csb_processing.py`

- `processing_workflow(files, vessel, output, ...)` — canonical end-to-end behavior anchor.
- Sequence: load config → parse → `cleaner.clean_data` → georeference → optional IWLS iteration loop → export data +
  metadata.
- IWLS loop iterates over Voronoi zones and excluded stations until `Depth_processed_meter` has no NaN or
  `max_iterations` reached.
- Completion criterion: `schema_ids.DEPTH_PROCESSED_METER` without NaN.

### `src/config/`

- `processing_config.py` — `CSBprocessingConfig` (top-level Pydantic model), `FileTypes` enum, `Filter` enum; duration
  regex `^\d+\s*(min|h)$`.
- `iwls_api_config.py` — `IWLSConfig`, `CacheConfig`; `CacheConfig.validate_cache_path` resolves relative paths and
  creates the folder.
- `caris_config.py` — `CarisAPIConfig`; validates CARIS install paths before run.
- `helper.py` — `load_config(config_file: Path)` with `@lru_cache`; `get_data_config()`, `get_caris_api_config()`.

### `src/ingestion/`

- `parser_abc.py` — abstract `DataParserABC` with `from_files()`.
- `factory_parser.py` — `FACTORY_PARSER` dict + `get_files_parser()` entry point.
- `parser_models.py` — `ParserFiles` dataclass; `DATA_TYPE_MAPPING`; `MultipleParsersError`.
- Implementations: `parser_dcdb.py`, `parser_black_box.py`, `parser_lowrance.py`, `parser_ofm.py`, `parser_b12_csb.py`,
  `parser_wibl.py`, `parser_hydroblock.py`.
- `warning_capture.py` — captures parser warnings without propagation.

### `src/filter/`

- `clean_and_filter.py` — pipeline entry: chains all active filters from config.
- `data_cleaning.py` — `clean_data()` — main cleaning function called by `processing_workflow`.
- `filtering.py` — core filter dispatcher.
- Individual filters: `datetime_filter.py`, `depth_filter.py`, `position_filter.py`, `speed_filter.py`.
- `outlier/` — outlier detection algorithms.
- `filter_models.py` — filter config Pydantic models.

### `src/transformation/`

- `georeference.py` — `georeference_bathymetry()` — applies waterline, sounder offset, water level correction, TVU/THU
  computation.
- `transformation_models.py` — `SensorProtocol`, `WaterlineProtocol` (structural typing for sensor injection).
- `uncertainty/` — TVU and THU computation modules.
- `order/` — IHO order classification support.

### `src/tide/`

- `voronoi/voronoi_algorithm.py` — Voronoi diagram computation from station positions.
- `voronoi/voronoi_geodataframe.py` — `get_voronoi_geodataframe()`, `get_station_title()`.
- `voronoi/voronoi_models.py` — Voronoi model types.
- `tide_zone_processing.py` — `add_tide_zone_id_to_geodataframe()` (rename contract: `id/code/name` → `Tide_zone_*`);
  `get_intersected_tide_zone_info()`.
- `time_serie/time_serie_dataframe.py` — `get_water_level_data_for_stations()` — fetches and interpolates IWLS time
  series per zone.
- `time_serie/time_serie_models.py` — time series data models.
- `time_serie/time_serie_retry.py` — retry logic for time series fetching.
- `water_level_export.py` — `export_station_water_levels()`, `plot_water_levels()`.
- `stations/factory_stations.py` — `get_stations_handler()` factory (private/public).
- `stations/stations_private.py`, `stations_public.py` — IWLS station implementations.
- `stations/cache_wrapper.py` — station data caching.

### `src/export/`

- `export_helpers.py` — `get_export_file_name()` (`CH-<logger>-<vessel>-<start>-<end>` convention);
  `finalize_geodataframe()`; `export_processed_data_and_metadata()`.
- `factory_export.py` — `FACTORY_EXPORT_GEODATAFRAME` dict; `export_geodataframe()` entry point.
- `export_format.py` — per-format implementations; CARIS imports are **runtime-only** (inside functions).
- `crs.py` — CRS helpers for export.
- `path.py` — `get_data_structure()` — creates `Data/`, `Tide/`, `Log/` directories.
- `geotiff.py` — GeoTIFF raster export helpers.

### `src/metadata/`

- `metadata_models.py` — `ProcessingMetadata` and related dataclasses.
- `export.py` — HTML metadata report generation.
- `pdf_export.py` — PDF metadata report (WeasyPrint or equivalent).
- `plot.py` — spatial coverage plot.
- `order/` — IHO order metadata helpers.

### `src/vessel/`

- `vessel_config.py` — `VesselConfig`, `Sounder`, `Waterline` dataclasses.
- `vessel_models.py` — Pydantic vessel configuration models.
- `vessel_config_manager_abc.py` — abstract `VesselConfigManagerABC`.
- `vessel_config_json_manager.py` — JSON-backed manager; resolves relative paths from `Path(__file__).parent.parent`.
- `vessel_config_sqlite_manager.py` — SQLite-backed manager.
- `factory_vessel_config.py` — `get_vessel_config()` — resolves `str` ID or passes through `VesselConfig`.
- `factory_vessel_config_manager.py` — `get_vessel_config_manager()` factory.
- `unknown_vessel_config.py` — `UNKNOWN_VESSEL_CONFIG` fallback (lever arms = 0).

### `src/schema/`

- `model.py` — Pandera schemas: `DataLoggerSchema`, `DataLoggerWithTideZoneSchema`, `TideZoneStationSchema`,
  `WaterLevelSerieDataWithMetaDataSchema`.
- `model_ids.py` — Column name constants (`DEPTH_PROCESSED_METER`, `TIME_UTC`, `TIDE_ZONE_ID`, …).

> **When adding/changing dataframe columns:** update `model.py` first, then tide/georeference transforms, then
`export_helpers.py::finalize_geodataframe()`.

### `src/iwls_api_request/`

- `api_facade.py` — `get_iwls_api()` factory; `EnvironmentType` (`dev`/`prod`/`public`); `HandlerType`.
- `api/iwls_private.py`, `api/iwls_public.py` — private/public API implementations.
- `api/iwls_api_abc.py` — `IWLSapiABC` protocol.
- `api/endpoint.py` — `Endpoint`, `EndpointType` models.
- `handler/http_query_handler.py` — `RateLimiterHandler`, `RequestsHandler`, `CachedSessionConfig`,
  `get_retry_adapter()`.
- `handler/models_handler.py` — `RetryAdapterConfig`.

### `src/caris_api/` (optional — CSAR export only)

- `pyapi/export_csar_api.py` — CSAR export via CARIS Python API (requires BASE Editor 6.1).
- `pyapi/import_caris_module.py` — `CarisModuleImporter` — dynamic import guard.
- `caris_batch/export_csar_batch.py` — CSAR export via carisbatch.exe CLI fallback.
- `model_caris.py` — CARIS data models.

> **Never import from `caris_api/` at module level.** All imports must be inside functions to avoid hard dependency
> failures when CARIS is absent.

---

## External Dependencies

| Dependency           | Version        | Usage                                                   |
|----------------------|----------------|---------------------------------------------------------|
| Python               | 3.11           | Required (CARIS API constraint if CSAR export used)     |
| geopandas            | pip            | Spatial data processing (GeoDataFrame)                  |
| pandas               | pip            | Tabular data, time series                               |
| numpy                | pip            | Vectorized numerical computation                        |
| pandera              | pip            | DataFrame schema validation (`src/schema/model.py`)     |
| pydantic             | pip            | Config model validation (`src/config/`)                 |
| loguru               | pip            | Logging (`src/logger/loguru_config.py`)                 |
| click                | pip            | CLI (`src/cli.py`)                                      |
| nicegui              | pip            | Web UI (`src/web_ui.py`, `src/app/`)                    |
| shapely              | pip            | Geometry operations (Voronoi, spatial joins)            |
| pyproj               | pip            | CRS transformations                                     |
| requests             | pip            | HTTP client for IWLS API                                |
| requests-ratelimiter | pip            | Rate limiting for IWLS API requests                     |
| requests-cache       | pip            | Optional HTTP caching for IWLS API                      |
| cachetools           | pip            | `LRUCache` in `transformation/georeference.py`          |
| CARIS BASE Editor    | 6.1 (optional) | CSAR export — `C:\Program Files\CARIS\BASE Editor\6.1\` |

> Install dependencies with `uv`: `uv sync`

---

## Tests

- `tests/` is currently **empty** — no automated test suite.
- **Validate changes with targeted CLI runs:**

```powershell
# Smoke test — process command
python src/cli.py process <file> --output <dir>

# Verify output structure
Get-ChildItem <dir>   # must contain Data/, Tide/, Log/

# Convert command
python src/cli.py convert <file.gpkg> --output <dir> --format geojson

# Web UI
python src/web_ui.py
```

- **IWLS validation:** run with `--apply-water-level True` and check that `Tide/StationVoronoi-1.gpkg` is produced.
- **CSAR validation:** run with `--format csar` and verify graceful failure when CARIS is absent.

---

## Important Reference Files

| File                                 | Purpose                                                      |
|--------------------------------------|--------------------------------------------------------------|
| `src/csb_processing.py`              | Canonical workflow — behavior anchor for all feature changes |
| `src/CONFIG_csb-processing.toml`     | Executable defaults — source of truth for all options        |
| `src/config/processing_config.py`    | `CSBprocessingConfig` Pydantic model (all config sections)   |
| `src/config/helper.py`               | `load_config()` with `@lru_cache`                            |
| `src/schema/model.py`                | Pandera schemas — update first for any column changes        |
| `src/schema/model_ids.py`            | Column name constants — always import from here              |
| `src/ingestion/factory_parser.py`    | Parser factory — register new parsers here                   |
| `src/ingestion/parser_models.py`     | `ParserFiles`, `DATA_TYPE_MAPPING`                           |
| `src/export/factory_export.py`       | Export factory — register new formats here                   |
| `src/export/export_helpers.py`       | `get_export_file_name()`, `finalize_geodataframe()`          |
| `src/logger/loguru_config.py`        | `configure_logger()` — centralized loguru setup              |
| `src/iwls_api_request/api_facade.py` | `get_iwls_api()` — IWLS client factory                       |
| `src/app/processing_handler.py`      | UI workflow mirror — keep in sync with `cli.py`              |
| `src/tide/tide_zone_processing.py`   | Tide-zone join contract (`id/code/name` → `Tide_zone_*`)     |
| `flow.mermaid`                       | Visual mirror of `processing_workflow` branches              |

---

## Behavioral Guidelines (Agent Mode)

These rules apply when operating as an autonomous coding agent (Claude Code, Copilot agent, etc.).
**Bias toward caution over speed.** For trivial tasks, use judgment.

### Before Starting Any Task

1. **Read before writing.** Always read the relevant file(s) before editing them.
2. **Search `src/` sub-packages first.** Before implementing any utility, verify it doesn't already exist
   in the relevant sub-package. If it exists, use it — never reimplement.
3. **Check `AGENTS.md` and `flow.mermaid`** for workflow invariants and safe extension paths.
4. **State assumptions.** If the request is ambiguous, state your interpretation explicitly before coding.
5. **Present tradeoffs.** If multiple valid approaches exist, name them — don't pick silently.

### Boundaries — What NOT to Touch

- **`src/caris_api/`** — CARIS integration. Do not modify unless explicitly asked. Keep all imports runtime-only.
- **`src/schema/model.py`** — Pandera schemas are the data contract. Never remove or rename columns without being asked.
- **`src/CONFIG_csb-processing.toml`** — Source of truth for defaults. Only add keys, never remove or rename without
  being asked.
- **Pre-existing dead code** — Mention it, don't delete it. Only remove code that YOUR changes made orphaned.

### During Implementation

- **Surgical edits.** Every changed line must trace directly to the user's request.
- **Match existing style.** Even if you'd do it differently — don't improve unrelated adjacent code.
- **Short functions.** If a function exceeds ~30 lines, extract helpers.
- **CLI / UI parity.** If you change file acceptance logic, update **both** `src/cli.py` and
  `src/app/processing_handler.py`.
- **Schema first.** If you add/change DataFrame columns, update `src/schema/model.py` before touching transformations or
  exports.

### After Each File Change

1. **Check for errors.** Verify the modified file has no syntax or import errors before continuing.
2. **Fix your orphans.** Remove imports/variables made unused by YOUR changes.
3. **Don't cascade.** If a change requires touching more than 3 files you didn't plan to touch, stop and ask.

### When to Stop and Ask

Stop and ask the user when:

- A change to `src/schema/model.py` would break existing callers across more than 2 modules.
- The task requires modifying CARIS integration (`src/caris_api/`).
- You're about to delete or overwrite a file you didn't create.
- The requirement is contradictory or has two equally valid interpretations.
- A workflow change in `csb_processing.py` would break the invariants documented in `flow.mermaid`.
