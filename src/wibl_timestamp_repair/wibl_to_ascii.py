"""Convert WIBL binary logger data to timestamped CSV/ASCII files.

The conversion logic is exposed through :func:`convert_wibl_to_ascii` and can
also be invoked from the command line.

Requires the WIBL Python package (https://github.com/CCOMJHC/WIBL).

Copyright 2023 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
Hydrographic Center, University of New Hampshire.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import ingestion.wibl.core.timestamping as ts


@dataclass(frozen=True)
class ConversionResult:
    """Summary returned by :func:`convert_wibl_to_ascii`."""

    logger_name: str
    platform_name: str
    depth_records: int
    heading_records: int | None = None
    temperature_records: int | None = None
    wind_records: int | None = None


@dataclass(frozen=True)
class BatchConversionItem:
    """Outcome for one input file in a batch conversion."""

    input_file: Path
    output_file: Path
    result: ConversionResult | None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Whether this file was converted successfully."""
        return self.error is None and self.result is not None


def _format_utc(epoch_seconds: float) -> str:
    """Format Unix time as an ISO-8601 UTC timestamp ending in ``Z``."""
    return (
        datetime.fromtimestamp(float(epoch_seconds), tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _write_series(
    output_path: str | Path,
    header: str,
    series: Mapping[str, Any],
    value_key: str,
    value_format: str,
) -> int:
    """Write one timestamped data series and return its record count."""
    times = series["t"]
    longitudes = series["lon"]
    latitudes = series["lat"]
    values = series[value_key]

    count = len(times)
    if not (len(longitudes) == len(latitudes) == len(values) == count):
        raise ValueError(f"Inconsistent array lengths in WIBL series '{value_key}'.")

    with Path(output_path).open("w", encoding="utf-8", newline="") as output:
        output.write(header + "\n")
        for epoch, longitude, latitude, value in zip(
            times, longitudes, latitudes, values
        ):
            output.write(
                f"{_format_utc(epoch)},{float(epoch):.3f},"
                f"{float(longitude):.8f},{float(latitude):.8f},"
                f"{format(float(value), value_format)}\n"
            )
    return count


def convert_wibl_to_ascii(
    input_file: str | Path,
    output_file: str | Path,
    *,
    heading_file: str | Path | None = None,
    temperature_file: str | Path | None = None,
    wind_file: str | Path | None = None,
    bitsize: int = 32,
) -> ConversionResult:
    """Convert a WIBL binary file into one or more timestamped text files.

    Args:
        input_file: WIBL binary input path.
        output_file: Output path for depth records (CSV text).
        heading_file: Optional output path for heading records.
        temperature_file: Optional output path for water-temperature records.
        wind_file: Optional output path for wind direction/speed records.
        bitsize: Bit length used to unwrap elapsed times; defaults to 32.

    Returns:
        A ``ConversionResult`` containing logger/platform metadata and record
        counts. Optional record counts are ``None`` when that output was not
        requested.

    Raises:
        ValueError: If ``bitsize`` is not a non-negative integer or a requested
            data series is absent/inconsistent.
        ts.NoTimeSource / ts.NoData: Propagated from the WIBL timestamp parser
            when the input cannot be timestamped or contains no data.
        OSError: If an input/output file cannot be accessed.
    """
    if isinstance(bitsize, bool) or not isinstance(bitsize, int) or bitsize < 0:
        raise ValueError("bitsize must be a non-negative integer.")

    input_path = Path(input_file)
    output_path = Path(output_file)
    elapsed_time_quantum = 1 << bitsize
    tsdata = ts.time_interpolation(str(input_path), elapsed_time_quantum)

    if "depth" not in tsdata:
        raise ValueError("The WIBL input contains no depth series.")

    depth_count = _write_series(
        output_path,
        "Time,Epoch,Longitude,Latitude,Depth",
        tsdata["depth"],
        "z",
        ".2f",
    )

    heading_count = None
    if heading_file is not None:
        if "heading" not in tsdata:
            raise ValueError(
                "A heading output was requested, but no heading series is available."
            )
        heading_count = _write_series(
            heading_file,
            "Time,Epoch,Longitude,Latitude,Heading",
            tsdata["heading"],
            "heading",
            ".1f",
        )

    temperature_count = None
    if temperature_file is not None:
        if "watertemp" not in tsdata:
            raise ValueError(
                "A temperature output was requested, but no water-temperature series is available."
            )
        temperature_count = _write_series(
            temperature_file,
            "Time,Epoch,Longitude,Latitude,Temperature",
            tsdata["watertemp"],
            "temperature",
            ".1f",
        )

    wind_count = None
    if wind_file is not None:
        if "wind" not in tsdata:
            raise ValueError(
                "A wind output was requested, but no wind series is available."
            )
        # Wind has two value columns, so write it separately.
        series = tsdata["wind"]
        count = len(series["t"])
        if not (
            len(series["lon"])
            == len(series["lat"])
            == len(series["direction"])
            == len(series["speed"])
            == count
        ):
            raise ValueError("Inconsistent array lengths in WIBL wind series.")
        with Path(wind_file).open("w", encoding="utf-8", newline="") as output:
            output.write("Time,Epoch,Longitude,Latitude,Direction,Speed\n")
            for epoch, longitude, latitude, direction, speed in zip(
                series["t"],
                series["lon"],
                series["lat"],
                series["direction"],
                series["speed"],
            ):
                output.write(
                    f"{_format_utc(epoch)},{float(epoch):.3f},"
                    f"{float(longitude):.8f},{float(latitude):.8f},"
                    f"{float(direction):.2f},{float(speed):.2f}\n"
                )
        wind_count = count

    return ConversionResult(
        logger_name=str(tsdata.get("loggername", "")),
        platform_name=str(tsdata.get("platform", "")),
        depth_records=depth_count,
        heading_records=heading_count,
        temperature_records=temperature_count,
        wind_records=wind_count,
    )


def find_wibl_files(
    directory: str | Path,
    *,
    recursive: bool = False,
) -> list[Path]:
    """Return sorted paths to WIBL raw files with three-digit numeric extensions.

    WIBL logger files use extensions such as ``.0``, ``.1`` and ``.2``.
    The filename stem is unrestricted; a file is selected when its extension
    consists of exactly three digits. Set ``recursive=True`` to include
    subdirectories. Text outputs such as ``wibl-raw.000.txt`` are excluded
    automatically because their final extension is ``.txt``.

    Args:
        directory: Directory to search.
        recursive: If true, search the directory tree recursively.

    Returns:
        A sorted list of matching file paths. Paths are not resolved, so they
        retain the directory form supplied by the caller.

    Raises:
        NotADirectoryError: If ``directory`` does not exist or is not a directory.
    """
    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    matches = root.rglob("*") if recursive else root.glob("*")
    return sorted(
        (path for path in matches if path.is_file() and path.suffix[1:].isdigit()),
        key=lambda path: str(path).casefold(),
    )


def convert_wibl_files_to_directory(
    input_files: list[str | Path] | tuple[str | Path, ...],
    output_directory: str | Path,
    *,
    bitsize: int = 32,
) -> list[BatchConversionItem]:
    """Convert multiple WIBL files to text files in one directory.

    Each output filename preserves the complete original filename and appends
    ``.txt`` (for example, ``wibl-raw.8`` becomes ``wibl-raw.8.txt``).
    A failed file is recorded in the returned list and does not stop the batch.

    Args:
        input_files: Iterable of WIBL input paths.
        output_directory: Directory where output text files will be written.
        bitsize: Bit length used to unwrap elapsed times (default: 32).

    Returns:
        One :class:`BatchConversionItem` per input file, in input order. Check
        ``item.succeeded`` and ``item.error`` to identify conversion failures.

    Raises:
        OSError: If the output directory cannot be created.
        ValueError: If ``bitsize`` is invalid.
    """
    if isinstance(bitsize, bool) or not isinstance(bitsize, int) or bitsize < 0:
        raise ValueError("bitsize must be a non-negative integer.")

    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)

    items: list[BatchConversionItem] = []
    for file in input_files:
        source = Path(file)
        output = destination / f"{source.name}.txt"
        try:
            result = convert_wibl_to_ascii(source, output, bitsize=bitsize)
        except (ts.NoTimeSource, ts.NoData, OSError, ValueError) as exc:
            items.append(
                BatchConversionItem(
                    input_file=source, output_file=output, result=None, error=str(exc)
                )
            )
        else:
            items.append(
                BatchConversionItem(
                    input_file=source, output_file=output, result=result
                )
            )
    return items


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser; no conversion logic lives here."""
    parser = argparse.ArgumentParser(
        description="Convert WIBL logger data to timestamped ASCII/CSV files."
    )
    parser.add_argument("input", help="WIBL binary input file")
    parser.add_argument("output", help="Output text/CSV file for depth")
    parser.add_argument(
        "-b",
        "--bitsize",
        type=int,
        default=32,
        help="Bit length of elapsed times (default: 32)",
    )
    parser.add_argument("-q", "--heading", help="Optional output file for true heading")
    parser.add_argument(
        "-t", "--temp", help="Optional output file for water temperature"
    )
    parser.add_argument(
        "-w", "--wind", help="Optional output file for wind speed/direction"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; argument parsing and presentation only."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = convert_wibl_to_ascii(
            args.input,
            args.output,
            heading_file=args.heading,
            temperature_file=args.temp,
            wind_file=args.wind,
            bitsize=args.bitsize,
        )
    except (ts.NoTimeSource, ts.NoData, OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")

    print("Converting data for:")
    print(f"Logger name:\t{result.logger_name}")
    print(f"Platform name:\t{result.platform_name}")
    print(f"Depth records:\t{result.depth_records}")
    if result.heading_records is not None:
        print(f"Heading records:\t{result.heading_records}")
    if result.temperature_records is not None:
        print(f"Temperature records:\t{result.temperature_records}")
    if result.wind_records is not None:
        print(f"Wind records:\t{result.wind_records}")
    return 0


if __name__ == "__main__":
    # files = find_wibl_files(Path(r"D:\WIBL\logs"))
    # convert_wibl_files_to_directory(files, Path(r"D:\WIBL\output"))
    convert_wibl_to_ascii(Path(r"D:\WIBL\wibl-raw.27"), Path(r"D:\WIBL\wibl-raw.txt"))
    # raise SystemExit(main())
