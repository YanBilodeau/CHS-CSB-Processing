"""Core implementation for position-aware WIBL timestamp repair.

Public API: :func:`repair_wibl_timestamps_position_aware`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

KNOT_TO_MPS = 0.5144444444444445
EARTH_RADIUS_M = 6_371_008.8


@dataclass(frozen=True)
class RepairResult:
    input_file: Path
    output_file: Path
    rows: int
    anchors: int
    corrected_rows: int
    unresolved_rows: int
    nominal_seconds_per_row: float
    segment_boundaries: int
    temporal_gap_candidates: int
    report_file: Path | None
    gap_report_file: Path | None


def _utc_cutoff(value: str | datetime | pd.Timestamp | None) -> pd.Timestamp:
    if value is None:
        return pd.Timestamp(datetime.now(timezone.utc))
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise ValueError("Invalid --valid-until timestamp.")
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _parse_times(values: pd.Series) -> pd.Series:
    try:
        return pd.to_datetime(values, utc=True, errors="coerce", format="mixed")
    except (TypeError, ValueError):
        return values.map(
            lambda value: pd.to_datetime(value, utc=True, errors="coerce")
        )


def _find_column(columns: Sequence[object], target: str) -> str | None:
    for column in columns:
        if str(column).strip().casefold() == target.casefold():
            return str(column)
    return None


def haversine_distances(longitude: np.ndarray, latitude: np.ndarray) -> np.ndarray:
    """Distance in metres between each adjacent position pair."""
    if len(longitude) < 2:
        return np.array([], dtype=float)
    lon1, lon2 = np.radians(longitude[:-1]), np.radians(longitude[1:])
    lat1, lat2 = np.radians(latitude[:-1]), np.radians(latitude[1:])
    valid = (
        np.isfinite(lon1)
        & np.isfinite(lon2)
        & np.isfinite(lat1)
        & np.isfinite(lat2)
        & (np.abs(latitude[:-1]) <= 90)
        & (np.abs(latitude[1:]) <= 90)
        & (np.abs(longitude[:-1]) <= 180)
        & (np.abs(longitude[1:]) <= 180)
    )
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    result = 2.0 * EARTH_RADIUS_M * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    result[~valid] = np.nan
    return result


def _estimate_global_period(
    anchor_indices: np.ndarray, anchor_ns: np.ndarray
) -> tuple[float, np.ndarray]:
    """Estimate a fallback record period; return all anchor-to-anchor rates."""
    if len(anchor_indices) < 2:
        raise ValueError("At least two trustworthy timestamp anchors are required.")
    row_spans = np.diff(anchor_indices).astype(float)
    elapsed = np.diff(anchor_ns).astype(float) / 1e9
    rates = elapsed / row_spans
    valid = np.isfinite(rates) & (rates > 0)
    if not valid.any():
        raise ValueError(
            "Could not estimate a positive sampling interval from timestamp anchors."
        )
    nominal = float(np.median(rates[valid]))
    normal = valid & (rates >= nominal * 0.25) & (rates <= nominal * 2.5)
    if normal.any():
        nominal = float(np.median(rates[normal]))
    return nominal, rates


def _is_position_spike(
    i: int, lon: np.ndarray, lat: np.ndarray, threshold_m: float
) -> bool:
    """Return True if row i+1 jumps away and immediately returns to the prior track."""
    if i < 0 or i + 2 >= len(lon):
        return False
    x, y = lon[i : i + 3], lat[i : i + 3]
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        return False
    d01 = haversine_distances(x[:2], y[:2])[0]
    d12 = haversine_distances(x[1:], y[1:])[0]
    d02 = haversine_distances(x[[0, 2]], y[[0, 2]])[0]
    return bool(d01 > threshold_m and d12 > threshold_m and d02 <= threshold_m)


def _local_periods(
    anchor_indices: np.ndarray,
    anchor_rates: np.ndarray,
    global_period: float,
    candidate_cuts: set[int],
    *,
    window: int = 7,
) -> np.ndarray:
    """Estimate local cadence while excluding the interval being tested and intervals spanning position jumps."""
    result = np.empty(len(anchor_rates), dtype=float)
    for k, current_rate in enumerate(anchor_rates):
        samples: list[float] = []
        for j in range(max(0, k - window), min(len(anchor_rates), k + window + 1)):
            if j == k:
                continue
            left, right = int(anchor_indices[j]), int(anchor_indices[j + 1])
            if any(left <= cut < right for cut in candidate_cuts):
                continue
            rate = float(anchor_rates[j])
            # The global upper bound protects the local estimate from intervals
            # already inflated by an unlocated data gap.
            if (
                math.isfinite(rate)
                and global_period * 0.25 <= rate <= global_period * 1.5
            ):
                samples.append(rate)
        local = float(np.median(samples)) if samples else global_period
        # A local rate is only a baseline. Never exceed the interval's own mean
        # duration per row; any excess is assigned to the detected gap(s).
        observed = float(current_rate)
        result[k] = (
            min(local, observed) if math.isfinite(observed) and observed > 0 else local
        )
    return result


def _edge_period(
    side: str,
    anchor_indices: np.ndarray,
    anchor_rates: np.ndarray,
    local_periods: np.ndarray,
    candidate_cuts: set[int],
    suspicious_pairs: set[tuple[int, int]],
    fallback: float,
) -> float:
    """Estimate cadence near the first/last valid anchor for file-edge extrapolation."""
    candidates = []
    for k, (left, right) in enumerate(zip(anchor_indices[:-1], anchor_indices[1:])):
        left, right = int(left), int(right)
        if (left, right) in suspicious_pairs:
            continue
        if any(left <= cut < right for cut in candidate_cuts):
            continue
        rate = float(anchor_rates[k])
        if not math.isfinite(rate) or not fallback * 0.25 <= rate <= fallback * 1.5:
            continue
        candidates.append((k, rate))
    if not candidates:
        return fallback
    candidates.sort(key=lambda item: item[0])
    selected = candidates[:8] if side == "leading" else candidates[-8:]
    return float(np.median([rate for _, rate in selected]))


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8", lineterminator="\n")
    temporary.replace(path)


def repair_wibl_timestamps_position_aware(
    input_file: str | Path,
    output_file: str | Path,
    *,
    valid_until: str | datetime | pd.Timestamp | None = None,
    max_speed_knots: float = 40.0,
    gap_factor: float = 2.5,
    min_gap_excess_seconds: float = 30.0,
    position_jump_margin: float = 1.5,
    report_file: str | Path | None = None,
    gap_report_file: str | Path | None = None,
) -> RepairResult:
    """Repair corrupt times without interpolating blindly through likely gaps."""
    source, destination = Path(input_file), Path(output_file)
    cutoff = _utc_cutoff(valid_until)
    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    if source.resolve() == destination.resolve():
        raise ValueError("Refusing to overwrite the input file.")
    for name, value in {
        "max_speed_knots": max_speed_knots,
        "gap_factor": gap_factor,
        "min_gap_excess_seconds": min_gap_excess_seconds,
        "position_jump_margin": position_jump_margin,
    }.items():
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite positive value.")

    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    if df.empty:
        raise ValueError(f"Input file has no data rows: {source}")
    time_col = _find_column(df.columns, "Time")
    epoch_col = _find_column(df.columns, "Epoch")
    lon_col = _find_column(df.columns, "Longitude")
    lat_col = _find_column(df.columns, "Latitude")
    if not time_col or not lon_col or not lat_col:
        raise ValueError("Required columns: Time, Longitude, Latitude.")

    original_times = df[time_col].copy()
    parsed = _parse_times(df[time_col])
    anchor_mask = (parsed.notna() & (parsed <= cutoff)).to_numpy()
    anchors = np.flatnonzero(anchor_mask)
    if len(anchors) < 2:
        raise ValueError(
            f"Only {len(anchors)} valid anchors found; at least two are required."
        )
    parsed_ns = parsed.astype("int64", copy=False).to_numpy()
    anchor_ns = parsed_ns[anchors]
    if np.any(np.diff(anchor_ns) <= 0):
        bad = int(np.flatnonzero(np.diff(anchor_ns) <= 0)[0])
        raise ValueError(
            "Trustworthy timestamp anchors are not strictly increasing near rows "
            f"{anchors[bad] + 1} and {anchors[bad + 1] + 1}."
        )

    lon = pd.to_numeric(df[lon_col], errors="coerce").to_numpy(dtype=float)
    lat = pd.to_numeric(df[lat_col], errors="coerce").to_numpy(dtype=float)
    row_count = len(df)
    distances = haversine_distances(lon, lat)
    global_period, anchor_rates = _estimate_global_period(anchors, anchor_ns)

    # First pass: position discontinuities that exceed the distance a vessel
    # could plausibly travel in one normal record interval.
    initial_threshold = (
        max_speed_knots * KNOT_TO_MPS * global_period * position_jump_margin + 3.0
    )
    raw_jump_candidates: set[int] = set()
    spike_rows: set[int] = set()
    for i, distance in enumerate(distances):
        if np.isfinite(distance) and distance > initial_threshold:
            if _is_position_spike(i, lon, lat, initial_threshold):
                spike_rows.add(i + 1)  # the isolated middle point
            else:
                raw_jump_candidates.add(i)

    # Local cadence helps catch smaller discontinuities in areas where the
    # logging cadence is faster than the whole-file median.
    periods_initial = _local_periods(
        anchors, anchor_rates, global_period, raw_jump_candidates
    )
    period_per_row = np.full(row_count, global_period, dtype=float)
    for k, (left, right) in enumerate(zip(anchors[:-1], anchors[1:])):
        period_per_row[int(left) : int(right)] = periods_initial[k]
    if anchors[0] > 0:
        period_per_row[: int(anchors[0])] = periods_initial[0]
    if anchors[-1] < row_count - 1:
        period_per_row[int(anchors[-1]) :] = periods_initial[-1]
    per_step_threshold = (
        max_speed_knots * KNOT_TO_MPS * period_per_row[:-1] * position_jump_margin + 3.0
    )
    for i, distance in enumerate(distances):
        if not np.isfinite(distance) or distance <= per_step_threshold[i]:
            continue
        if _is_position_spike(i, lon, lat, float(per_step_threshold[i])):
            spike_rows.add(i + 1)
            raw_jump_candidates.discard(i)
        else:
            raw_jump_candidates.add(i)

    # Final local cadence, excluding candidate jump intervals.
    local_periods = _local_periods(
        anchors, anchor_rates, global_period, raw_jump_candidates
    )
    temporal_events: list[dict[str, object]] = []
    temporal_flags: dict[tuple[int, int], dict[str, object]] = {}
    warning_pairs: set[tuple[int, int]] = set()
    severe_pairs: set[tuple[int, int]] = set()
    for k, (left, right) in enumerate(zip(anchors[:-1], anchors[1:])):
        left, right = int(left), int(right)
        elapsed = (int(parsed_ns[right]) - int(parsed_ns[left])) / 1e9
        span = right - left
        observed_per_row = elapsed / span
        base_period = float(local_periods[k])
        expected = span * base_period
        excess = elapsed - expected
        ratio = observed_per_row / base_period
        severe = bool(ratio >= gap_factor and excess >= min_gap_excess_seconds)
        warning = bool(ratio >= 1.25 and excess >= min_gap_excess_seconds)
        temporal_flags[(left, right)] = {
            "elapsed": elapsed,
            "span": span,
            "observed_per_row": observed_per_row,
            "base_period": base_period,
            "expected": expected,
            "excess": excess,
            "ratio": ratio,
            "severe": severe,
            "warning": warning,
        }
        if severe:
            severe_pairs.add((left, right))
            warning_pairs.add((left, right))
        elif warning:
            warning_pairs.add((left, right))
        else:
            continue
        temporal_events.append(
            {
                "event_type": (
                    "temporal_gap_candidate" if severe else "cadence_anomaly_warning"
                ),
                "left_anchor_row": left + 1,
                "right_anchor_row": right + 1,
                "elapsed_seconds": round(elapsed, 6),
                "records_between_anchors": span - 1,
                "observed_seconds_per_row": round(observed_per_row, 6),
                "estimated_local_seconds_per_row": round(base_period, 6),
                "expected_seconds_at_local_cadence": round(expected, 6),
                "excess_seconds_over_local_cadence": round(excess, 6),
                "observed_to_local_cadence_ratio": round(ratio, 6),
                "severe_gap_candidate": severe,
                "position_boundary_rows": "",
                "handling": "pending_position_check",
            }
        )

    # Candidate cuts only make sense where a pair of valid anchors brackets them.
    cut_by_pair: dict[tuple[int, int], list[int]] = {}
    for left, right in zip(anchors[:-1], anchors[1:]):
        pair = (int(left), int(right))
        contained = sorted(i for i in raw_jump_candidates if pair[0] <= i < pair[1])
        if contained:
            cut_by_pair[pair] = contained

    corrected_ns = np.zeros(row_count, dtype=np.int64)
    assigned = np.zeros(row_count, dtype=bool)
    corrected_ns[anchors] = anchor_ns
    assigned[anchors] = True
    status = np.full(row_count, "unresolved_no_anchor", dtype=object)
    status[anchors] = "anchor_preserved"
    accepted_cuts: dict[int, str] = {}
    unresolved_intervals: list[tuple[int, int]] = []
    position_events: list[dict[str, object]] = []
    cut_to_distance: dict[int, float] = {}

    # Solve each anchor-bounded interval independently.
    for k, (left, right) in enumerate(zip(anchors[:-1], anchors[1:])):
        left, right = int(left), int(right)
        pair = (left, right)
        span = right - left
        flags = temporal_flags[pair]
        cut_indices = cut_by_pair.get(pair, [])
        elapsed = float(flags["elapsed"])
        base_period = float(flags["base_period"])

        if cut_indices:
            # Baseline time is assigned to normal steps; any excess elapsed time
            # is concentrated at the position discontinuity(ies), not smeared
            # across all rows. This recreates a temporal gap while preserving both anchors.
            durations = np.full(span, base_period, dtype=float)
            total_base = base_period * span
            surplus = max(0.0, elapsed - total_base)
            weights = np.array(
                [max(float(distances[i]), 0.1) for i in cut_indices], dtype=float
            )
            weights = weights / weights.sum()
            for cut, weight in zip(cut_indices, weights):
                durations[cut - left] += surplus * float(weight)

            # Enforce minimum elapsed time implied by maximum vessel speed.
            min_cut_dt = {
                cut: float(distances[cut]) / (max_speed_knots * KNOT_TO_MPS)
                for cut in cut_indices
            }
            for cut in cut_indices:
                slot = cut - left
                if durations[slot] < min_cut_dt[cut]:
                    durations[slot] = min_cut_dt[cut]
            # Rebalance the non-cut steps so the right anchor remains exact.
            non_cut_slots = [j for j in range(span) if (left + j) not in cut_indices]
            residual = elapsed - sum(durations[cut - left] for cut in cut_indices)
            feasible = residual > 0
            if feasible and non_cut_slots:
                normal_period = residual / len(non_cut_slots)
                feasible = base_period * 0.25 <= normal_period <= base_period * 2.5
                if feasible:
                    for slot in non_cut_slots:
                        durations[slot] = normal_period
            elif feasible and not non_cut_slots:
                total_minimum = sum(durations[cut - left] for cut in cut_indices)
                feasible = math.isclose(
                    total_minimum, elapsed, rel_tol=0.0, abs_tol=0.01
                )
            if feasible and (
                np.any(durations <= 0)
                or not math.isclose(
                    float(durations.sum()), elapsed, rel_tol=0.0, abs_tol=0.01
                )
            ):
                feasible = False

            if feasible:
                running_ns = int(parsed_ns[left])
                for slot, step_seconds in enumerate(durations, start=1):
                    row = left + slot
                    if row == right:
                        corrected_ns[row] = int(parsed_ns[right])
                    else:
                        running_ns += int(round(float(step_seconds) * 1e9))
                        corrected_ns[row] = running_ns
                        assigned[row] = True
                        status[row] = "position_aware_reconstruction"
                for cut in cut_indices:
                    accepted_cuts[cut] = "position_discontinuity_gap"
                    cut_to_distance[cut] = float(distances[cut])
                    status[cut] = (
                        "segment_end_before_gap"
                        if not anchor_mask[cut]
                        else status[cut]
                    )
                    if cut + 1 < right and not anchor_mask[cut + 1]:
                        status[cut + 1] = "segment_start_after_gap"
                if pair in warning_pairs:
                    handling = "split_at_position_boundary_and_reconstruct"
                else:
                    handling = "split_at_position_boundary_and_reconstruct"
            else:
                # The anchor interval cannot accommodate the max-speed constraint
                # without implausibly compressing the other intervals.
                unresolved_intervals.append(pair)
                status[left + 1 : right] = "unresolved_spatial_time_conflict"
                handling = "unresolved_spatial_time_conflict"
            for event in temporal_events:
                if (
                    event["left_anchor_row"] == left + 1
                    and event["right_anchor_row"] == right + 1
                ):
                    event["position_boundary_rows"] = ";".join(
                        str(i + 1) for i in cut_indices
                    )
                    event["handling"] = handling
        else:
            # Without a position boundary, do not manufacture a chronology across
            # intervals whose duration is inconsistent with the local cadence.
            if pair in warning_pairs and span > 1:
                status[left + 1 : right] = (
                    "unresolved_temporal_gap_no_position_boundary"
                )
                unresolved_intervals.append(pair)
                handling = "unresolved_no_position_boundary"
                for event in temporal_events:
                    if (
                        event["left_anchor_row"] == left + 1
                        and event["right_anchor_row"] == right + 1
                    ):
                        event["handling"] = handling
                continue
            if span > 1:
                positions = np.arange(left + 1, right, dtype=np.int64)
                total_ns = int(parsed_ns[right]) - int(parsed_ns[left])
                corrected_ns[positions] = int(parsed_ns[left]) + (
                    total_ns * (positions - left) // span
                )
                assigned[positions] = True
                status[positions] = "interpolated_between_anchors"

    # File-edge rows can be extrapolated from nearby non-suspicious anchors.
    suspicious_pairs = set(warning_pairs)
    leading_period = _edge_period(
        "leading",
        anchors,
        anchor_rates,
        local_periods,
        raw_jump_candidates,
        suspicious_pairs,
        global_period,
    )
    trailing_period = _edge_period(
        "trailing",
        anchors,
        anchor_rates,
        local_periods,
        raw_jump_candidates,
        suspicious_pairs,
        global_period,
    )
    first, last = int(anchors[0]), int(anchors[-1])
    for row in range(first - 1, -1, -1):
        corrected_ns[row] = int(parsed_ns[first]) - int(
            round((first - row) * leading_period * 1e9)
        )
        assigned[row] = True
        status[row] = "extrapolated_before_first_anchor"
    for row in range(last + 1, row_count):
        corrected_ns[row] = int(parsed_ns[last]) + int(
            round((row - last) * trailing_period * 1e9)
        )
        assigned[row] = True
        status[row] = "extrapolated_after_last_anchor"

    # Segment labels reflect only accepted position boundaries.
    segment_id = np.ones(row_count, dtype=int)
    current = 1
    for i in range(row_count - 1):
        segment_id[i] = current
        if i in accepted_cuts:
            current += 1
    segment_id[-1] = current

    # Check all assigned timestamps in file order. Unresolved intervals are skipped,
    # but the timestamps on either side must still be chronologically ordered.
    assigned_ix = np.flatnonzero(assigned)
    if len(assigned_ix) > 1:
        differences = np.diff(corrected_ns[assigned_ix])
        if np.any(differences <= 0):
            bad = int(np.flatnonzero(differences <= 0)[0])
            raise ValueError(
                "Reconstructed assigned timestamps are not increasing near rows "
                f"{assigned_ix[bad] + 1} and {assigned_ix[bad + 1] + 1}. "
                "Review the anchors or reduce automatic reconstruction."
            )

    # Format repaired Time/Epoch. Rows whose time could not be inferred are blank,
    # but all bathymetry and position rows remain in the output.
    time_text = np.full(row_count, "", dtype=object)
    epoch_text = np.full(row_count, "", dtype=object)
    for i in np.flatnonzero(assigned):
        timestamp = pd.Timestamp(int(corrected_ns[i]), tz="UTC")
        time_text[i] = timestamp.isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        epoch_text[i] = f"{corrected_ns[i] / 1e9:.3f}"
    df[time_col] = time_text
    if epoch_col is None:
        df.insert(df.columns.get_loc(time_col) + 1, "Epoch", epoch_text)
    else:
        df[epoch_col] = epoch_text

    # Build row-level QA report and position/time gap event report.
    dist_next = np.full(row_count, np.nan)
    if row_count > 1:
        dist_next[:-1] = distances
    elapsed_next = np.full(row_count, np.nan)
    speed_next = np.full(row_count, np.nan)
    for i in range(row_count - 1):
        if assigned[i] and assigned[i + 1] and segment_id[i] == segment_id[i + 1]:
            dt = (int(corrected_ns[i + 1]) - int(corrected_ns[i])) / 1e9
            elapsed_next[i] = dt
            if dt > 0 and np.isfinite(distances[i]):
                speed_next[i] = distances[i] / dt / KNOT_TO_MPS

    report_frame = pd.DataFrame(
        {
            "data_row": np.arange(1, row_count + 1),
            "segment_id": segment_id,
            "timestamp_status": status,
            "anchor_preserved": anchor_mask,
            "original_time": original_times,
            "corrected_time": time_text,
            "timestamp_assigned": assigned,
            "longitude": lon,
            "latitude": lat,
            "distance_to_next_m": np.round(dist_next, 3),
            "elapsed_to_next_s_within_segment": np.round(elapsed_next, 6),
            "derived_speed_to_next_knots": np.round(speed_next, 3),
            "position_jump_candidate_after_row": [
                i in raw_jump_candidates for i in range(row_count)
            ],
            "segment_boundary_after_row": [
                i in accepted_cuts for i in range(row_count)
            ],
            "segment_boundary_reason": [
                accepted_cuts.get(i, "") for i in range(row_count)
            ],
            "speed_over_max_flag": [
                bool(np.isfinite(v) and v > max_speed_knots) for v in speed_next
            ],
            "isolated_position_spike_row": [i in spike_rows for i in range(row_count)],
            # An independent screening estimate: distance divided by expected local
            # record interval, without using the suspect timestamps being repaired.
            "implied_speed_knots_at_nominal_cadence": np.round(
                distances / (period_per_row[:-1] * KNOT_TO_MPS), 3
            ).tolist()
            + [np.nan],
            "implied_speed_over_max_at_nominal_cadence": [
                bool(np.isfinite(value) and value > max_speed_knots)
                for value in (distances / (period_per_row[:-1] * KNOT_TO_MPS)).tolist()
                + [np.nan]
            ],
        }
    )

    position_events = []
    for i in sorted(raw_jump_candidates):
        inside_pair = next(
            (
                (left, right)
                for left, right in zip(anchors[:-1], anchors[1:])
                if int(left) <= i < int(right)
            ),
            None,
        )
        position_events.append(
            {
                "event_type": "large_position_step",
                "row_before": i + 1,
                "row_after": i + 2,
                "distance_m": round(float(distances[i]), 3),
                "maximum_speed_knots": max_speed_knots,
                "distance_threshold_m": round(float(per_step_threshold[i]), 3),
                "inside_anchor_interval": bool(inside_pair is not None),
                "inside_temporal_warning_interval": (
                    bool(inside_pair in warning_pairs) if inside_pair else False
                ),
                "used_as_segment_boundary": i in accepted_cuts,
                "handling": (
                    "segment_boundary"
                    if i in accepted_cuts
                    else "flag_only_not_bracketed_or_time_conflict"
                ),
            }
        )
    for row in sorted(spike_rows):
        position_events.append(
            {
                "event_type": "isolated_position_spike",
                "row_before": row - 1,
                "row_after": row + 1,
                "middle_row": row,
                "distance_threshold_m": round(
                    float(per_step_threshold[max(0, row - 2)]), 3
                ),
                "used_as_segment_boundary": False,
                "handling": "flag_only_coordinate_may_be_bad",
            }
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    _atomic_csv(df, destination)
    report_path = Path(report_file) if report_file else None
    if report_path:
        _atomic_csv(report_frame, report_path)
    gap_path = Path(gap_report_file) if gap_report_file else None
    if gap_path:
        _atomic_csv(pd.DataFrame(temporal_events + position_events), gap_path)

    corrected_count = int((assigned & ~anchor_mask).sum())
    unresolved_count = int((~assigned).sum())
    return RepairResult(
        input_file=source,
        output_file=destination,
        rows=row_count,
        anchors=int(anchor_mask.sum()),
        corrected_rows=corrected_count,
        unresolved_rows=unresolved_count,
        nominal_seconds_per_row=global_period,
        segment_boundaries=len(accepted_cuts),
        temporal_gap_candidates=len(warning_pairs),
        report_file=report_path,
        gap_report_file=gap_path,
    )
