"""Categorical, time-series, histogram, and scatter aggregation over records.

All functions return plain row dicts (each with `references` + `total_contributors`)
plus optional notes. They are pure and deterministic — the numeric source of truth.
"""

from __future__ import annotations

from collections import defaultdict

from app.agg import extractors as ex
from app.agg.citations import build_references
from app.schemas import Dimension, Metric


def _metric_value(metric: Metric, enrollments: list[int]) -> float:
    if metric == Metric.enrollment_sum:
        return float(sum(enrollments))
    if metric == Metric.enrollment_avg:
        return round(sum(enrollments) / len(enrollments), 2) if enrollments else 0.0
    return float(len(enrollments)) if enrollments else 0.0  # not used for count path


def aggregate_categorical(
    studies: list[dict],
    dimension: Dimension,
    metric: Metric = Metric.count,
    value_field: str = "trial_count",
    limit: int | None = None,
    sort_desc: bool = True,
) -> tuple[list[dict], list[str]]:
    """Group studies by one dimension and compute a metric per group.

    Returns (rows, notes). Each row: {dimension_key, value_field, references,
    total_contributors}. Counts are de-duplicated per (study, group) so a study
    with two Phase-2 entries counts once toward Phase 2.
    """
    notes: list[str] = []
    # group -> list of (nct, field, raw); de-dup studies per group
    contributors: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    enrollments: dict[str, list[int]] = defaultdict(list)
    seen_pairs: set[tuple[str, str]] = set()

    for study in studies:
        nct = ex.nct_id(study)
        enroll = ex.enrollment_count(study)
        for label, field, raw in ex.extract_dimension(study, dimension):
            if (nct, label) in seen_pairs:
                continue
            seen_pairs.add((nct, label))
            contributors[label].append((nct, field, raw))
            if enroll is not None:
                enrollments[label].append(enroll)

    rows: list[dict] = []
    for label, contribs in contributors.items():
        if metric == Metric.count:
            val: float | int = len(contribs)
        else:
            val = _metric_value(metric, enrollments[label])
            if not enrollments[label]:
                notes.append(f"No enrollment data for '{label}'; treated as 0.")
        rows.append(
            {
                dimension.value: label,
                value_field: val,
                "total_contributors": len(contribs),
                "references": [r.model_dump() for r in build_references(contribs)],
            }
        )

    rows.sort(key=lambda r: r[value_field], reverse=sort_desc)
    if limit and len(rows) > limit:
        notes.append(f"Showing top {limit} of {len(rows)} '{dimension.value}' categories.")
        rows = rows[:limit]
    return rows, notes


def aggregate_grouped(
    studies: list[dict],
    primary: Dimension,
    secondary: Dimension,
    limit: int | None = None,
) -> tuple[list[dict], list[str]]:
    """Two-dimension counts for grouped bars. Rows: {primary, secondary, trial_count, ...}."""
    notes: list[str] = []
    contributors: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()

    for study in studies:
        nct = ex.nct_id(study)
        prim_vals = ex.extract_dimension(study, primary)
        sec_vals = ex.extract_dimension(study, secondary)
        for pl, pf, pr in prim_vals:
            for sl, _sf, _sr in sec_vals:
                key = (pl, sl)
                if (nct, pl, sl) in seen:
                    continue
                seen.add((nct, pl, sl))
                contributors[key].append((nct, pf, pr))

    rows = []
    for (pl, sl), contribs in contributors.items():
        rows.append(
            {
                primary.value: pl,
                secondary.value: sl,
                "trial_count": len(contribs),
                "total_contributors": len(contribs),
                "references": [r.model_dump() for r in build_references(contribs)],
            }
        )
    rows.sort(key=lambda r: r["trial_count"], reverse=True)
    if limit:
        rows = rows[:limit]
    return rows, notes


def aggregate_time_series(studies: list[dict], granularity: str = "year") -> tuple[list[dict], list[str]]:
    """Count studies per start-date bucket (year or YYYY-MM)."""
    notes: list[str] = []
    contributors: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    field = "protocolSection.statusModule.startDateStruct.date"
    missing = 0

    for study in studies:
        nct = ex.nct_id(study)
        date = study.get("protocolSection", {}).get("statusModule", {}).get("startDateStruct", {}).get("date")
        if not date or not date[:4].isdigit():
            missing += 1
            continue
        bucket = date[:4] if granularity == "year" else date[:7]
        contributors[bucket].append((nct, field, date))

    rows = []
    for bucket in sorted(contributors):
        contribs = contributors[bucket]
        rows.append(
            {
                "period": bucket,
                "trial_count": len(contribs),
                "total_contributors": len(contribs),
                "references": [r.model_dump() for r in build_references(contribs)],
            }
        )
    if missing:
        notes.append(f"{missing} trials excluded (no parseable start date).")
    return rows, notes


def aggregate_histogram(studies: list[dict], bins: int = 10) -> tuple[list[dict], list[str]]:
    """Bin enrollment counts into a histogram. Returns bucket rows."""
    notes: list[str] = []
    field = "protocolSection.designModule.enrollmentInfo.count"
    values: list[tuple[str, int]] = []
    for study in studies:
        v = ex.enrollment_count(study)
        if v is not None and v >= 0:
            values.append((ex.nct_id(study), v))

    if not values:
        return [], ["No enrollment data available to build a histogram."]

    nums = sorted(v for _, v in values)
    lo = nums[0]
    # Enrollment is heavily right-skewed (a few mega-trials enroll tens of
    # thousands). Cap the binned range at the 95th percentile and collect the
    # rest in a single overflow bin, so the bulk of the distribution is legible.
    cap = _percentile(nums, 0.95)
    if cap <= lo:
        cap = nums[-1]
    width = _nice_step(cap - lo, bins)
    if width <= 0:
        width = 1
    # Round the lower edge down to a multiple of width for tidy labels.
    base = (lo // width) * width
    top = base
    while top < cap:
        top += width  # first bin edge at/above the 95th percentile

    buckets: dict[int, list[tuple[str, str, str]]] = {}
    overflow: list[tuple[str, str, str]] = []
    for nct, v in values:
        if v >= top:
            overflow.append((nct, field, str(v)))
        else:
            idx = int((v - base) // width)
            buckets.setdefault(idx, []).append((nct, field, str(v)))

    rows = []
    n_bins = int((top - base) // width)
    for idx in range(n_bins):
        start = base + idx * width
        end = start + width
        contribs = buckets.get(idx, [])
        rows.append(
            {
                "bin_start": start,
                "bin_end": end,
                "bin_label": f"{_fmt(start)}–{_fmt(end)}",
                "trial_count": len(contribs),
                "total_contributors": len(contribs),
                "references": [r.model_dump() for r in build_references(contribs)],
            }
        )
    if overflow:
        rows.append(
            {
                "bin_start": top,
                "bin_end": nums[-1],
                "bin_label": f"{_fmt(top)}+",
                "trial_count": len(overflow),
                "total_contributors": len(overflow),
                "references": [r.model_dump() for r in build_references(overflow)],
            }
        )
        notes.append(
            f"{len(overflow)} trials with enrollment ≥ {_fmt(top)} grouped into a final "
            f"'{_fmt(top)}+' bin (max {_fmt(nums[-1])})."
        )
    notes.append(f"Enrollment binned in steps of {_fmt(width)} up to {_fmt(top)}.")
    return rows, notes


def _percentile(sorted_nums: list[int], q: float) -> int:
    """Value at quantile q (0..1) of an already-sorted list (nearest-rank)."""
    if not sorted_nums:
        return 0
    idx = min(len(sorted_nums) - 1, int(q * (len(sorted_nums) - 1) + 0.5))
    return sorted_nums[idx]


def _nice_step(span: int, target_bins: int) -> int:
    """Round a raw bin width up to a 'nice' 1/2/5 * 10^n value for readable axes."""
    import math

    if span <= 0 or target_bins <= 0:
        return 1
    raw = span / target_bins
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    norm = raw / mag
    if norm <= 1:
        nice = 1
    elif norm <= 2:
        nice = 2
    elif norm <= 5:
        nice = 5
    else:
        nice = 10
    return max(1, int(nice * mag))


def _fmt(n: int) -> str:
    """Compact integer label: 1500 -> '1.5k', 20000 -> '20k'."""
    if n >= 1000:
        s = f"{n / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{s}k"
    return str(int(n))


def aggregate_scatter(studies: list[dict]) -> tuple[list[dict], list[str]]:
    """One point per study: enrollment (x) vs duration in days (y).

    Enrollment/duration are extremely right-skewed (a few trials report millions of
    participants or multi-decade spans). We drop points beyond the 99th percentile
    of either axis so the bulk is legible, and disclose how many were excluded.
    """
    notes: list[str] = []
    points: list[tuple[str, int, int]] = []
    skipped = 0
    for study in studies:
        nct = ex.nct_id(study)
        enroll = ex.enrollment_count(study)
        dur = ex.duration_days(study)
        if enroll is None or dur is None or dur < 0:
            skipped += 1
            continue
        points.append((nct, enroll, dur))

    rows: list[dict] = []
    if not points:
        if skipped:
            notes.append(f"{skipped} trials skipped (missing enrollment or dates).")
        return rows, notes

    x_cap = _percentile(sorted(p[1] for p in points), 0.99)
    y_cap = _percentile(sorted(p[2] for p in points), 0.99)
    outliers = 0
    for nct, enroll, dur in points:
        if enroll > x_cap or dur > y_cap:
            outliers += 1
            continue
        rows.append(
            {
                "nct_id": nct,
                "enrollment": enroll,
                "duration_days": dur,
                "total_contributors": 1,
                "references": [
                    {
                        "nct_id": nct,
                        "field": "protocolSection.designModule.enrollmentInfo.count",
                        "value": str(enroll),
                    }
                ],
            }
        )
    if skipped:
        notes.append(f"{skipped} trials skipped (missing enrollment or dates).")
    if outliers:
        notes.append(
            f"{outliers} extreme outliers beyond the 99th percentile "
            f"(enrollment > {_fmt(x_cap)} or duration > {_fmt(y_cap)} days) excluded for readability."
        )
    return rows, notes
