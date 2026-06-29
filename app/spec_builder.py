"""Turn a QueryPlan + aggregated rows into a VisualizeResponse (encoding + data).

This is where dimension/metric/viz_type choices become concrete visual-channel
mappings. Pure and deterministic — no network, no LLM.
"""

from __future__ import annotations

from app.agg import aggregate as agg
from app.agg import geo as geo_agg
from app.agg import network as net_agg
from app.schemas import (
    Channel,
    Dimension,
    Encoding,
    Meta,
    Metric,
    QueryPlan,
    Visualization,
    VisualizeResponse,
    VizType,
)

_DIM_TITLE = {
    Dimension.phase: "Phase",
    Dimension.status: "Status",
    Dimension.sponsor: "Sponsor",
    Dimension.sponsor_class: "Sponsor Class",
    Dimension.country: "Country",
    Dimension.start_year: "Start Year",
    Dimension.study_type: "Study Type",
    Dimension.intervention: "Intervention",
    Dimension.intervention_type: "Intervention Type",
    Dimension.condition: "Condition",
    Dimension.enrollment: "Enrollment",
}


def _metric_title(metric: Metric) -> tuple[str, str]:
    """Return (value_field_name, axis_title)."""
    return {
        Metric.count: ("trial_count", "Number of Trials"),
        Metric.enrollment_sum: ("enrollment_sum", "Total Enrollment"),
        Metric.enrollment_avg: ("enrollment_avg", "Average Enrollment"),
    }[metric]


def build_response(
    plan: QueryPlan,
    studies: list[dict],
    total: int,
    filters_applied: dict,
    exact_rows: list[dict] | None = None,
    exact_notes: list[str] | None = None,
    aggregated_override: int | None = None,
) -> VisualizeResponse:
    """Build the response. If ``exact_rows`` is provided (faceted exact counts for
    bar/grouped), use them instead of aggregating the sampled records — the counts
    then reflect the full population, not a sample.

    ``aggregated_override`` sets ``trials_aggregated`` explicitly (and drives the
    sampling warning) for paths that supply pre-built rows from sampled records,
    e.g. the non-facetable cohort fallback."""
    exact = exact_rows is not None
    notes: list[str] = list(exact_notes or [])
    if plan.interpretation:
        pass  # kept in meta.query_interpretation
    sort_desc = plan.sort != "y_asc"
    limit = plan.limit
    value_field, value_title = _metric_title(plan.metric)

    viz = plan.viz_type

    if viz in (VizType.bar_chart,):
        dim = plan.dimension or Dimension.phase
        if exact:
            rows = exact_rows
        else:
            rows, n = agg.aggregate_categorical(studies, dim, plan.metric, value_field, limit, sort_desc)
            notes += n
        # For ordered dims like year/phase keep natural order when not count-sorted
        encoding = Encoding(
            x=Channel(field=dim.value, type="nominal", title=_DIM_TITLE.get(dim, dim.value)),
            y=Channel(field=value_field, type="quantitative", title=value_title),
        )
        data: list | dict = rows
        title = f"Trials by {_DIM_TITLE.get(dim, dim.value)}"

    elif viz == VizType.grouped_bar and plan.cohorts:
        # Comparison cohorts: one series per cohort (color field = "series").
        primary = plan.dimension or Dimension.phase
        rows = exact_rows if exact else []
        encoding = Encoding(
            x=Channel(field=primary.value, type="nominal", title=_DIM_TITLE.get(primary)),
            y=Channel(field="trial_count", type="quantitative", title="Number of Trials"),
            color=Channel(field="series", type="nominal", title="Cohort"),
        )
        data = rows
        labels = " vs. ".join(c.label for c in plan.cohorts)
        title = f"{labels} — Trials by {_DIM_TITLE.get(primary)}"

    elif viz == VizType.grouped_bar:
        primary = plan.dimension or Dimension.phase
        secondary = plan.secondary_dimension or Dimension.status
        if exact:
            rows = exact_rows
        else:
            rows, n = agg.aggregate_grouped(studies, primary, secondary, limit)
            notes += n
        encoding = Encoding(
            x=Channel(field=primary.value, type="nominal", title=_DIM_TITLE.get(primary)),
            y=Channel(field="trial_count", type="quantitative", title="Number of Trials"),
            color=Channel(field=secondary.value, type="nominal", title=_DIM_TITLE.get(secondary)),
        )
        data = rows
        title = f"Trials by {_DIM_TITLE.get(primary)} and {_DIM_TITLE.get(secondary)}"

    elif viz == VizType.time_series:
        rows, n = agg.aggregate_time_series(studies, plan.time_granularity.value)
        notes += n
        encoding = Encoding(
            x=Channel(field="period", type="temporal", title="Start Period"),
            y=Channel(field="trial_count", type="quantitative", title="Number of Trials"),
        )
        data = rows
        title = "Trials Started Over Time"

    elif viz == VizType.histogram:
        rows, n = agg.aggregate_histogram(studies)
        notes += n
        encoding = Encoding(
            x=Channel(field="bin_label", type="ordinal", title="Enrollment Range"),
            y=Channel(field="trial_count", type="quantitative", title="Number of Trials"),
        )
        data = rows
        title = "Distribution of Trial Enrollment Size"

    elif viz == VizType.scatter_plot:
        rows, n = agg.aggregate_scatter(studies)
        notes += n
        encoding = Encoding(
            x=Channel(field="enrollment", type="quantitative", title="Enrollment"),
            y=Channel(field="duration_days", type="quantitative", title="Duration (days)"),
        )
        data = rows
        title = "Enrollment vs. Study Duration"

    elif viz == VizType.network_graph:
        node_types = plan.network.node_types if plan.network else []
        edge_relation = plan.network.edge_relation if plan.network else None
        graph, n = net_agg.build_network(studies, node_types, edge_relation)
        notes += n
        encoding = Encoding(
            nodes={"id": "id", "label": "label", "group": "group", "weight": "weight"},
            edges={"source": "source", "target": "target", "weight": "weight"},
        )
        data = graph
        rel = edge_relation or "entity co-occurrence"
        title = f"Network of {rel.replace('-', ' & ')}"

    elif viz == VizType.geo_map:
        region_key = "country"
        result, n = geo_agg.aggregate_geo(studies, region_key, limit)
        notes += n
        encoding = Encoding(
            region=Channel(field="region", type="nominal", title="Country"),
            color=Channel(field="trial_count", type="quantitative", title="Number of Trials"),
            lat=Channel(field="lat", type="quantitative", title="Latitude"),
            lng=Channel(field="lng", type="quantitative", title="Longitude"),
        )
        data = result  # {regions: [...], points: [...]}
        title = "Geographic Distribution of Trials"

    else:  # pragma: no cover - schema-constrained
        raise ValueError(f"Unsupported viz_type: {viz}")

    sorting = None
    if viz in (VizType.bar_chart, VizType.grouped_bar, VizType.geo_map):
        sorting = "value desc" if sort_desc else "value asc"

    # Exact (faceted) results cover the full population; sampled results don't.
    if aggregated_override is not None:
        aggregated = aggregated_override
    else:
        aggregated = total if exact else len(studies)

    meta = Meta(
        filters=filters_applied,
        query_interpretation=plan.interpretation,
        total_matching_trials=total,
        trials_aggregated=aggregated,
        units="trials" if plan.metric == Metric.count else "participants",
        sorting=sorting,
        time_granularity=plan.time_granularity.value if viz == VizType.time_series else None,
        grouping=(
            "cohort comparison"
            if plan.cohorts
            else (plan.secondary_dimension.value if plan.secondary_dimension else None)
        ),
        notes=notes,
        warnings=_warnings(total, aggregated),
    )

    return VisualizeResponse(
        visualization=Visualization(type=viz, title=title, encoding=encoding, data=data),
        meta=meta,
    )


def _warnings(total: int, fetched: int) -> list[str]:
    warnings: list[str] = []
    if total and fetched < total:
        warnings.append(
            f"Aggregated over {fetched} of {total} matching trials (sampled most recent). "
            "Counts reflect the sample, not the full population."
        )
    if fetched == 0:
        warnings.append("No trials matched the query filters.")
    return warnings
