# WIBL timestamp repair package

Python API for position-aware repair of timestamps in WIBL-derived TXT/CSV tables. Raw WIBL files (`.0`, `.1`, `.2`, `.x`) can also be discovered by directory.

## Install

```bash
python -m pip install pandas numpy
python -m pip install -e .
```

## Repair one converted table

```python
from pathlib import Path
from wibl_timestamp_repair import repair_wibl_timestamps_position_aware

result = repair_wibl_timestamps_position_aware(
    input_file=r"D:\Survey\wibl-raw.8.txt",
    output_file=r"D:\Survey\repaired\wibl-raw.8.txt",
    valid_until="2026-10-20T23:59:59Z",  # Optional; default is current UTC time
    expected_record_frequency_hz=1.0,  # One output record per second
    report_file=r"D:\Survey\repaired\position_report.csv",
    gap_report_file=r"D:\Survey\repaired\gap_events.csv",
)
print(result.corrected_rows, result.unresolved_rows)
```


## Cadence-aware gap screening

Use `expected_record_frequency_hz` to specify the expected *output-record cadence* in records per second (not the sonar acoustic carrier frequency). For example, `1.0` means one record per second; `0.5` means one record every two seconds. This parameter is optional, so the existing inferred-local-cadence behavior remains the default.

```python
result = repair_wibl_timestamps_position_aware(
    input_file=r"D:\Survey\TXT\wibl-raw.8.txt",
    output_file=r"D:\Survey\repaired\wibl-raw.8.txt",
    expected_record_frequency_hz=1.0,
    gap_factor=2.5,
    min_gap_excess_seconds=30.0,
    gap_report_file=r"D:\Survey\repaired\gap_events.csv",
)
```

With a configured rate of 1 record/s, an interval of about 592 seconds across 138 row-to-row intervals is compared against about 138 expected seconds: about 454 excess seconds and 4.29 seconds/record. It is flagged as a severe gap candidate with the default thresholds. The configured cadence also informs position-jump thresholds, normal-step reconstruction and file-edge extrapolation. When no position boundary supports a warned interval, adaptive mode checks the observed mean period against adjacent clean cadence regimes: plausible medium-confidence cases can be reconstructed, while larger unexplained deviations remain unresolved by default. The gap-event report records both the inferred local cadence and configured reference cadence, expected elapsed time, excess time, ratio, adjacent regimes and the adaptive decision.

The setting is also passed through `repair_wibl_files` and `repair_wibl_directory`; the CLI option is `--expected-record-frequency-hz 1.0`.

## Adaptive cadence-regime reconstruction

The default `cadence_mode="adaptive"` compares a warned anchor interval's observed mean period with the cadence regimes estimated from nearby clean anchor intervals. It can reconstruct a warning at **medium confidence** when the period is within `adaptive_max_period_factor` (default `1.25`, or 25%) of an adjacent clean regime. Both valid anchor timestamps are preserved exactly.

```python
from wibl_timestamp_repair import repair_wibl_timestamps_position_aware

result = repair_wibl_timestamps_position_aware(
    input_file=r"D:\Survey\TXT\wibl-raw.8.txt",
    output_file=r"D:\Survey\repaired\wibl-raw.8.txt",
    expected_record_frequency_hz=1.0,
    cadence_mode="adaptive",
    adaptive_max_period_factor=1.25,
    adaptive_low_confidence_max_factor=1.5,
    adaptive_reconstruct_low_confidence=False,
    report_file=r"D:\Survey\repaired\position_report.csv",
    gap_report_file=r"D:\Survey\repaired\gap_events.csv",
)
print("Adaptive intervals:", result.adaptive_reconstructed_intervals)
print("Low-confidence intervals:", result.low_confidence_reconstructed_intervals)
print("Unresolved rows:", result.unresolved_rows)
```

In `strict` mode, warned intervals without a usable position boundary remain unresolved, as in the previous version. In adaptive mode, a candidate can be tagged `medium`, `low`, or `none`. The low-confidence option is deliberately opt-in because it can fill a section whose excess duration is also compatible with an unlocated logging gap:

```python
cadence_mode="adaptive",
adaptive_reconstruct_low_confidence=True,
```

The reports include the estimated cadence before and after the interval, the candidate interval's observed mean period, its deviation from the closest adjacent regime, a confidence label, a decision reason, and depth summary statistics when a `Depth` column exists. Depth is diagnostic only: it is not used as a deterministic cadence formula because depth alone does not establish the logging rate.

**Important limitation:** when all timestamps inside a span are invalid, there is no reliable evidence to locate a cadence change point inside that span. The algorithm therefore uses the interval's observed mean period to interpolate between its two valid anchors if the regime passes the configured plausibility rule; it does not invent a finer-grained piecewise change point. A section rejected by the adaptive rule remains unresolved unless the explicit low-confidence option is enabled.

For the supplied `wibl-raw.8.txt` example, the default adaptive setting reconstructed the interval between rows 5189 and 5353 at medium confidence (observed 1.440 s/record; adjacent regimes about 1.006 and 1.331 s/record), while rows 2917–3198 remained unresolved because their observed 1.825 s/record was about 38% away from the closest clean adjacent regime. Set `adaptive_reconstruct_low_confidence=True` to estimate that latter section too, but review it carefully: the program cannot determine whether its excess duration represents a genuine cadence regime or a gap without more evidence.

## Discover raw WIBL files (`.0`, `.1`, `.2`, `.x`)

```python
from wibl_timestamp_repair import discover_wibl_files

raw_files = discover_wibl_files(r"D:\Survey\WIBL", recursive=True)
for path in raw_files:
    print(path)
```

This function only locates the raw files; it does **not** decode/convert the binary WIBL format. Timestamp repair operates on converted TXT/CSV tables containing `Time`, `Longitude` and `Latitude` columns.

## Repair several converted tables

```python
from wibl_timestamp_repair import discover_wibl_tables, repair_wibl_files

inputs = discover_wibl_tables(r"D:\Survey\TXT", recursive=True)
batch = repair_wibl_files(
    inputs,
    output_directory=r"D:\Survey\TXT_repaired",
    valid_until="2026-10-20T23:59:59Z",
    expected_record_frequency_hz=1.0,
    write_reports=True,
)
print(f"Réussis : {batch.succeeded}; échecs : {batch.failed}")
for result in batch.results:
    print(result.input_file, "->", result.output_file)
for path, error in batch.errors.items():
    print(f"Échec : {path}: {error}")
```

`repair_wibl_files` processes all supplied files and records failures per file without stopping the batch. Outputs are named `<nom>.position_repaired.txt` or `.csv`; input files are never overwritten. If multiple inputs would create the same output name, the batch is rejected before processing to prevent collisions.

For a one-call directory workflow, use `repair_wibl_directory(input_directory, output_directory, recursive=True, ...)`. It finds converted TXT/CSV files with the required columns and repairs them.

## CLI

```bash
python -m wibl_timestamp_repair "D:\Survey\TXT" --recursive --report
```
