# AGENTS.md

## Project Snapshot
- CHS-CSB_Processing is a Python 3.11 pipeline that ingests raw bathymetry logs, cleans/filter tags soundings, georeferences with vessel sensors, optionally applies IWLS water-level reduction, then exports data + metadata.
- Core orchestration lives in `src/csb_processing.py` (`processing_workflow`). Treat this as the behavior anchor for feature changes.
- User entrypoints are thin wrappers over the same core flow: CLI in `src/cli.py` and NiceGUI in `src/web_ui.py` + `src/app/processing_handler.py`.

## Quick Start for Agents (read in this order)
- `src/csb_processing.py::processing_workflow(...)`: canonical end-to-end behavior.
- `src/cli.py::process_bathymetric_data(...)` and `src/cli.py::convert_gpkg(...)`: user-facing validation and defaults.
- `src/app/processing_handler.py::ProcessingHandler.process_files(...)`: UI path that must remain behavior-parity with CLI.
- `src/CONFIG_csb-processing.toml`: executable defaults for options, export formats, IWLS settings, CARIS section.
- `flow.mermaid`: visual mirror of the implemented branches (with/without water-level loop).

## Architecture and Data Flow
- Parser selection is factory-based in `src/ingestion/factory_parser.py` (`FACTORY_PARSER`): extension normalization + header matching.
- `ParserFiles` in `src/ingestion/parser_models.py` enforces a single parser type per run (mixed formats raise `MultipleParsersError`).
- Data contracts are Pandera models in `src/schema/model.py`; many functions assume `DataLoggerSchema` or `DataLoggerWithTideZoneSchema` columns/dtypes.
- `processing_workflow` sequence (`src/csb_processing.py`): load config -> parse -> `cleaner.clean_data` -> georeference -> optional IWLS iteration loop -> export data + metadata.
- Water-level mode iterates over Voronoi zones and excluded stations until `Depth_processed_meter` has no NaN or max iterations reached.
- `flow.mermaid` mirrors the implemented workflow; use it to reason about regressions across branches of the pipeline.

## Core Symbols and Invariants
- Output structure is fixed by `get_data_structure(...)` in `src/csb_processing.py`: `<output>/Data`, `<output>/Tide`, `<output>/Log`.
- Completion criterion for IWLS loop is `schema_ids.DEPTH_PROCESSED_METER` without NaN in `processing_workflow`.
- Export naming convention comes from `src/export/export_helpers.py::get_export_file_name(...)` (`CH-<logger>-<vessel>-<start>-<end>`).
- Final export schema projection uses `src/export/export_helpers.py::finalize_geodataframe(...)` and `schema.DataLoggerSchema.__annotations__.keys()`.
- Tide-zone join contract uses `src/tide/tide_zone_processing.py::add_tide_zone_id_to_geodataframe(...)` with renamed IDs (`id -> Tide_zone_id`, etc.).
- Config loading is cached (`@lru_cache`) in `src/config/helper.py::load_config(...)`; avoid side effects dependent on re-reading TOML within same process.

## Critical Developer Workflows
- Setup dependencies with uv (documented in `README.en.md` / `README.fr.md`): `uv sync`.
- Process files: `python src/cli.py process <files...> --output <dir>`.
- Convert already processed geospatial files: `python src/cli.py convert <files...> --output <dir> --format <fmt>` (input restricted to `.gpkg` / `.geojson`).
- Launch GUI: `python src/web_ui.py` (Windows helper script: `run_WebUI.bat`).
- Build docs from `docs/`: `make html` (or `make.bat html` on Windows).
- There is no automated test suite today (`tests/` is empty), so validate changes with targeted CLI/UI runs.

## Project-Specific Patterns (with examples)
- Logging pattern: module-level `LOGGER = logger.bind(name="...")` (examples: `CSB-Processing.WorkFlow`, `CSB-Processing.CLI`, `CSB-Processing.Export.Helpers`).
- CLI/UI parity pattern: file filtering logic is duplicated in `src/cli.py::is_valid_file/get_files` and `src/app/processing_handler.py::is_valid_file/get_files`.
- Vessel source exclusivity pattern: `--vessel` vs `--waterline` is enforced in CLI and validator/UI; keep both paths aligned.
- Relative path resolution pattern:
  - vessel config: `src/vessel/vessel_config_json_manager.py` resolves non-absolute paths from `Path(__file__).parent.parent`.
  - IWLS cache: `src/config/iwls_api_config.py::CacheConfig.validate_cache_path` resolves relative paths and creates folder.
- Duration validation pattern: regex `^\d+\s*(min|h)$` in both `src/config/processing_config.py` and `src/config/iwls_api_config.py`.
- Optional CARIS dependency pattern: runtime imports inside `src/export/export_format.py` (`from caris_api import ...` inside functions only).

## Integrations and Boundaries
- IWLS integration boundary: `src/iwls_api.py` initializes config/environment/API/station handler; HTTP handling lives in `src/iwls_api_request/*` (rate limiting, retry adapter, optional cache session).
- Tide computations are split between Voronoi (`src/tide/voronoi/*`), tide-zone mapping (`src/tide/tide_zone_processing.py`), and time-series fetch/interpolation (`src/tide/time_serie/*`).
- Export boundary is `export.export_processed_data_to_file_types(...)` in `src/export/export_helpers.py`; prefer extending export factory over branching callers.
- CARIS is optional globally but required for `csar` export; `src/config/caris_config.py` validates install paths before run.
- Keep runtime CARIS imports in `src/export/export_format.py` (`from caris_api import ...` inside functions) to avoid hard dependency failures when CARIS is absent.

## Change Playbooks (safe extension paths)
- Add a new raw input parser:
  - implement parser class under `src/ingestion/` following `DataParserABC` pattern,
  - register header/extension in `FACTORY_PARSER` (`src/ingestion/factory_parser.py`),
  - map parser -> logger type in `DATA_TYPE_MAPPING` (`src/ingestion/parser_models.py`).
- Add a new export format:
  - implement `export_geodataframe_to_<fmt>(...)` in `src/export/export_format.py`,
  - register in `FACTORY_EXPORT_GEODATAFRAME` (`src/export/factory_export.py`),
  - expose in `config.processing_config.FileTypes` and CLI `--format` choices.
- Add/change dataframe columns:
  - update `src/schema/model.py` first,
  - then update transformations (`cleaner`, `georeference`, tide-zone join),
  - then update export finalization (`finalize_geodataframe(...)`).
- Change workflow behavior:
  - verify both entrypoints (`src/cli.py` and `src/app/processing_handler.py`) still produce same processing parameters,
  - re-check loop termination and excluded station logic in `processing_workflow`.

## Safe Change Guidance for Agents
- If you change processing semantics, check both CLI (`src/cli.py`) and UI handler (`src/app/processing_handler.py`) because both call `processing_workflow`.
- When adding/changing dataframe columns, update Pandera schemas first, then downstream transformations/exports.
- Prefer adding new parser/export types via factories (`FACTORY_PARSER`, `FACTORY_EXPORT_GEODATAFRAME`) instead of command-level `if/else` branching.
- Treat `src/CONFIG_csb-processing.toml` as executable documentation for defaults and expected config shape.

## Validation Checklist Before Handover
- CLI path smoke test: run one `process` command and verify `Data/`, `Tide/`, `Log/` are created.
- UI parity check: confirm `ProcessingHandler` uses same vessel/waterline behavior as CLI defaults.
- If IWLS touched: verify station resolution and exclusions through one iteration (`StationVoronoi-<n>.gpkg` appears).
- If export touched: validate at least one vector format (`.gpkg`) and one tabular/raster format if modified.
- If `csar` touched: ensure missing CARIS still fails gracefully without breaking non-CSAR exports.

## Operational Recipes V2 (touch X -> modify Y/Z -> validate with C)
- If you touch workflow logic in `processing_workflow` -> check parity params in `src/cli.py::process_bathymetric_data` and `src/app/processing_handler.py::_run_processing_workflow` -> validate with `python src/cli.py process <file> --output <dir>`.
- If you touch file acceptance rules -> update both `src/cli.py::is_valid_file/get_files` and `src/app/processing_handler.py::is_valid_file/get_files` -> validate with one CLI run and one UI run (`python src/web_ui.py`).
- If you add parser support -> add parser class under `src/ingestion/`, register in `src/ingestion/factory_parser.py::FACTORY_PARSER`, then map in `src/ingestion/parser_models.py::DATA_TYPE_MAPPING` -> validate with `python src/cli.py process <new-format-file> --output <dir>`.
- If you add export format -> implement `export_geodataframe_to_<fmt>(...)` in `src/export/export_format.py`, register in `src/export/factory_export.py::FACTORY_EXPORT_GEODATAFRAME`, expose in `config.processing_config.FileTypes` and CLI `--format` -> validate with `python src/cli.py convert <input.gpkg> --output <dir> --format <fmt>`.
- If you change dataframe columns/types -> update `src/schema/model.py` first (`DataLoggerSchema` / `DataLoggerWithTideZoneSchema`), then tide/georeference transforms, then `src/export/export_helpers.py::finalize_geodataframe` -> validate with one `process` run and output read of `.gpkg`.
- If you touch tide-zone joins -> preserve rename contract in `src/tide/tide_zone_processing.py::add_tide_zone_id_to_geodataframe` (`id/code/name` -> `Tide_zone_*`) -> validate with IWLS-enabled run and check non-empty tide-zone columns.
- If you touch IWLS behavior -> review `src/iwls_api.py::initialize_iwls_api`, `src/tide/time_serie/*`, and loop termination on `schema_ids.DEPTH_PROCESSED_METER` in `processing_workflow` -> validate that `Tide/StationVoronoi-<n>.gpkg` is produced.
- If you touch config semantics -> update validators in `src/config/processing_config.py` / `src/config/iwls_api_config.py` and keep `"<number> <min|h>"` duration pattern -> validate by running CLI with default and custom `--config`.
- If you touch CARIS/CSAR -> keep runtime imports inside `src/export/export_format.py` and path checks in `src/config/caris_config.py` -> validate both `--format csar` (with CARIS) and non-CSAR formats (without CARIS).
- If you touch docs-facing behavior -> update relevant README section and keep `flow.mermaid` consistent with `processing_workflow` branches -> validate docs build from `docs/` using `make html` or `make.bat html`.

