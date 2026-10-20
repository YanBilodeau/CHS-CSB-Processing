"""Batch helpers for discovering raw WIBL files and repairing converted tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from .repair import RepairResult, _find_column, repair_wibl_timestamps_position_aware

WIBL_EXTENSIONS = frozenset({".0", ".1", ".2", ".x"})
TABLE_EXTENSIONS = frozenset({".txt", ".csv"})


@dataclass(frozen=True)
class BatchRepairResult:
    """Summary of a batch run; individual failures do not hide successful results."""

    results: tuple[RepairResult, ...]
    errors: dict[Path, str]

    @property
    def succeeded(self) -> int:
        return len(self.results)

    @property
    def failed(self) -> int:
        return len(self.errors)


def discover_wibl_files(
    directory: str | Path, *, recursive: bool = False
) -> list[Path]:
    """Return raw WIBL files with extensions .0, .1, .2 or .x in a directory.

    Matching is case-insensitive. Results are sorted by path. This only discovers
    raw files; it does not convert them to the TXT/CSV table expected by repair.
    """
    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError(f"WIBL directory does not exist: {root}")
    iterator = root.rglob("*") if recursive else root.iterdir()
    return sorted(
        (
            path
            for path in iterator
            if path.is_file() and path.suffix.casefold() in WIBL_EXTENSIONS
        ),
        key=lambda path: str(path).casefold(),
    )


def _is_repairable_table(path: Path) -> bool:
    try:
        columns = pd.read_csv(path, nrows=0).columns
    except (OSError, UnicodeDecodeError, pd.errors.ParserError, ValueError):
        return False
    return all(
        _find_column(columns, name) is not None
        for name in ("Time", "Longitude", "Latitude")
    )


def discover_wibl_tables(
    directory: str | Path, *, recursive: bool = False
) -> list[Path]:
    """Find converted TXT/CSV tables with the columns needed by the repair API."""
    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {root}")
    iterator = root.rglob("*") if recursive else root.iterdir()
    return sorted(
        (
            path
            for path in iterator
            if path.is_file()
            and path.suffix.casefold() in TABLE_EXTENSIONS
            and _is_repairable_table(path)
        ),
        key=lambda path: str(path).casefold(),
    )


def repair_wibl_files(
    input_files: Iterable[str | Path],
    output_directory: str | Path,
    *,
    valid_until: str | datetime | pd.Timestamp | None = None,
    max_speed_knots: float = 40.0,
    gap_factor: float = 2.5,
    min_gap_excess_seconds: float = 30.0,
    position_jump_margin: float = 1.5,
    write_reports: bool = True,
    expected_record_frequency_hz: float | None = None,
    cadence_mode: str = "adaptive",
    adaptive_max_period_factor: float = 1.25,
    adaptive_low_confidence_max_factor: float = 1.5,
    adaptive_reconstruct_low_confidence: bool = False,
) -> BatchRepairResult:
    """Repair multiple converted TXT/CSV files into one output directory.

    Inputs are never overwritten. Output files are named
    ``<stem>.position_repaired<suffix>``. To avoid accidental overwrites, duplicate
    output names in the input collection are rejected before any file is processed.
    Per-file errors are captured in ``BatchRepairResult.errors`` and processing
    continues for the remaining files.
    """
    sources = [Path(path) for path in input_files]
    if not sources:
        raise ValueError("input_files must contain at least one file.")
    output_root = Path(output_directory)
    destinations = [
        output_root / f"{source.stem}.position_repaired{source.suffix}"
        for source in sources
    ]
    folded_names = [path.name.casefold() for path in destinations]
    if len(folded_names) != len(set(folded_names)):
        raise ValueError(
            "Several input files would produce the same output filename. "
            "Pass a unique set of input files or separate them into batches."
        )

    output_root.mkdir(parents=True, exist_ok=True)
    successes: list[RepairResult] = []
    errors: dict[Path, str] = {}
    for source, destination in zip(sources, destinations):
        try:
            report_path = (
                destination.with_name(destination.stem + ".position_report.csv")
                if write_reports
                else None
            )
            gap_path = (
                destination.with_name(destination.stem + ".gap_events.csv")
                if write_reports
                else None
            )
            result = repair_wibl_timestamps_position_aware(
                source,
                destination,
                valid_until=valid_until,
                max_speed_knots=max_speed_knots,
                gap_factor=gap_factor,
                min_gap_excess_seconds=min_gap_excess_seconds,
                position_jump_margin=position_jump_margin,
                expected_record_frequency_hz=expected_record_frequency_hz,
                cadence_mode=cadence_mode,
                adaptive_max_period_factor=adaptive_max_period_factor,
                adaptive_low_confidence_max_factor=adaptive_low_confidence_max_factor,
                adaptive_reconstruct_low_confidence=adaptive_reconstruct_low_confidence,
                report_file=report_path,
                gap_report_file=gap_path,
            )
            successes.append(result)
        except Exception as exc:
            errors[source] = f"{type(exc).__name__}: {exc}"
    return BatchRepairResult(results=tuple(successes), errors=errors)


def repair_wibl_directory(
    input_directory: str | Path,
    output_directory: str | Path,
    *,
    recursive: bool = False,
    **repair_options: object,
) -> BatchRepairResult:
    """Discover repairable TXT/CSV tables in a directory and repair them in batch."""
    sources = discover_wibl_tables(input_directory, recursive=recursive)
    if not sources:
        raise FileNotFoundError(
            f"No TXT/CSV tables with Time, Longitude and Latitude found in {input_directory}."
        )
    return repair_wibl_files(sources, output_directory, **repair_options)
