"""Command-line interface; delegates all repair logic to the public API."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

from .repair import RepairResult, _find_column, repair_wibl_timestamps_position_aware


def _looks_like_time_table(path: Path) -> bool:
    try:
        columns = pd.read_csv(path, nrows=0).columns
    except (OSError, UnicodeDecodeError, pd.errors.ParserError):
        return False
    return all(
        _find_column(columns, name) is not None
        for name in ("Time", "Longitude", "Latitude")
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Position-aware WIBL timestamp repair."
    )
    parser.add_argument("input", type=Path, help="Input TXT/CSV file or directory.")
    parser.add_argument(
        "-o", "--output", type=Path, help="Output path for a single input file."
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Output directory for directory input."
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Search subdirectories recursively."
    )
    parser.add_argument(
        "--valid-until",
        help="Last valid UTC timestamp (ISO-8601); default is current UTC time.",
    )
    parser.add_argument(
        "--max-speed-knots",
        type=float,
        default=40.0,
        help="Plausible maximum vessel speed in knots (default 40).",
    )
    parser.add_argument(
        "--gap-factor",
        type=float,
        default=2.5,
        help="Strong-gap threshold relative to the reference cadence (configured rate if provided; otherwise inferred local cadence; default 2.5).",
    )
    parser.add_argument(
        "--min-gap-excess-seconds",
        type=float,
        default=30.0,
        help="Minimum excess duration for a possible gap (default 30 seconds).",
    )
    parser.add_argument(
        "--position-jump-margin",
        type=float,
        default=1.5,
        help="Safety margin on max-speed distance per record (default 1.5).",
    )
    parser.add_argument(
        "--expected-record-frequency-hz",
        type=float,
        help=(
            "Expected output-record cadence in records/second (e.g. 1.0 for one record per second); "
            "used as an independent baseline to flag suspicious anchor intervals."
        ),
    )
    parser.add_argument(
        "--cadence-mode",
        choices=("adaptive", "strict"),
        default="adaptive",
        help="Adaptive reconstruction for plausible cadence regimes (default) or strict conservative mode.",
    )
    parser.add_argument(
        "--adaptive-max-period-factor",
        type=float,
        default=1.25,
        help="Maximum relative deviation from an adjacent clean cadence regime for medium confidence (default 1.25).",
    )
    parser.add_argument(
        "--adaptive-low-confidence-max-factor",
        type=float,
        default=1.5,
        help="Maximum relative deviation eligible for low-confidence reconstruction (default 1.5).",
    )
    parser.add_argument(
        "--adaptive-reconstruct-low-confidence",
        action="store_true",
        help="Also reconstruct low-confidence intervals; may interpolate across an unlocated gap.",
    )
    parser.add_argument(
        "--anchor-inconsistency-margin-seconds",
        type=float,
        default=30.0,
        help=(
            "Minimum time-envelope violation needed to reject a conflicting anchor "
            "automatically (default 30 s). Smaller conflicts are left unresolved."
        ),
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write row-level QA and gap-event CSV reports.",
    )
    return parser


def _process_one(
    source: Path, destination: Path, args: argparse.Namespace
) -> RepairResult:
    report_path = (
        destination.with_name(destination.stem + ".position_repair_report.csv")
        if args.report
        else None
    )
    gap_path = (
        destination.with_name(destination.stem + ".gap_events.csv")
        if args.report
        else None
    )
    result = repair_wibl_timestamps_position_aware(
        source,
        destination,
        valid_until=args.valid_until,
        max_speed_knots=args.max_speed_knots,
        gap_factor=args.gap_factor,
        min_gap_excess_seconds=args.min_gap_excess_seconds,
        position_jump_margin=args.position_jump_margin,
        expected_record_frequency_hz=args.expected_record_frequency_hz,
        cadence_mode=args.cadence_mode,
        adaptive_max_period_factor=args.adaptive_max_period_factor,
        adaptive_low_confidence_max_factor=args.adaptive_low_confidence_max_factor,
        adaptive_reconstruct_low_confidence=args.adaptive_reconstruct_low_confidence,
        anchor_inconsistency_margin_seconds=args.anchor_inconsistency_margin_seconds,
        report_file=report_path,
        gap_report_file=gap_path,
    )
    print(
        f"[OK] {source.name}: {result.corrected_rows:,} timestamps corrected, {result.anchors:,} anchors, "
        f"{result.unresolved_rows:,} rows unresolved, "
        f"{result.rejected_timestamp_anchors:,} conflicting anchors rejected, "
        f"{result.ambiguous_anchor_conflicts:,} ambiguous anchor conflicts, "
        f"{result.segment_boundaries} segment boundaries, "
        f"{result.adaptive_reconstructed_intervals} adaptive intervals "
        f"({result.low_confidence_reconstructed_intervals} low-confidence); "
        f"fallback cadence={result.nominal_seconds_per_row:.3f} s/row -> {destination}"
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    source = args.input
    try:
        if source.is_file():
            if args.output_dir is not None and args.output is not None:
                parser.error("Use either --output or --output-dir, not both.")
            destination = (
                args.output
                if args.output
                else (args.output_dir or source.parent)
                / f"{source.stem}.position_repaired{source.suffix}"
            )
            _process_one(source, destination, args)
            return 0
        if not source.is_dir():
            parser.error(f"Input path does not exist: {source}")
        if args.output is not None:
            parser.error("--output is only valid for a single file; use --output-dir.")
        output_root = (
            args.output_dir or source.parent / f"{source.name}_position_repaired"
        )
        iterator = source.rglob("*") if args.recursive else source.glob("*")
        files = sorted(
            path
            for path in iterator
            if path.is_file()
            and path.suffix.casefold() in {".txt", ".csv"}
            and _looks_like_time_table(path)
            and not path.resolve().is_relative_to(output_root.resolve())
        )
        if not files:
            parser.error(
                f"No TXT/CSV containing Time, Longitude and Latitude found in {source}."
            )
        errors = 0
        for item in files:
            try:
                _process_one(item, output_root / item.relative_to(source), args)
            except Exception as exc:
                errors += 1
                print(f"[ERROR] {item}: {exc}", file=sys.stderr)
        return 1 if errors else 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
