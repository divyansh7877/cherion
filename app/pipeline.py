"""Orchestration: request -> plan -> fetch -> aggregate -> spec.

The single coherent path every query flows through, regardless of type.
"""

from __future__ import annotations

from app.agg import aggregate as agg
from app.clinicaltrials import facet_exec
from app.clinicaltrials.client import CTGovClient
from app.clinicaltrials.params import params_for_plan
from app.planner import plan_query
from app.schemas import Dimension, QueryPlan, VisualizeRequest, VisualizeResponse, VizType
from app.spec_builder import build_response

_DEFAULT_MAX_RECORDS = 1000


def _filters_applied(plan: QueryPlan) -> dict:
    return {k: v for k, v in plan.filters.model_dump().items() if v not in (None, [], "")}


async def run_pipeline(request: VisualizeRequest, client: CTGovClient | None = None) -> VisualizeResponse:
    client = client or CTGovClient()
    plan = plan_query(request)
    filters_applied = _filters_applied(plan)

    # Comparison cohorts ('A vs B'): grouped bar, one series per cohort, split by
    # `dimension`. Exact via faceted counts when the dimension is a bounded enum;
    # otherwise per-cohort record fetch (sampled, honestly flagged).
    if plan.cohorts:
        if facet_exec.can_facet_cohorts(plan.cohorts, plan.dimension):
            rows, total, notes = await facet_exec.faceted_cohort_comparison(
                client,
                plan.filters,
                plan.cohorts,
                plan.dimension or Dimension.phase,
                limit=plan.limit,
            )
            return build_response(plan, [], total, filters_applied, exact_rows=rows, exact_notes=notes)
        rows, total, fetched, notes = await _cohort_record_fetch(client, plan, request)
        return build_response(
            plan,
            [],
            total,
            filters_applied,
            exact_rows=rows,
            exact_notes=notes,
            aggregated_override=fetched,
        )

    # Fast exact path: count-based bar/grouped over bounded-enum dimensions are
    # computed via faceted countTotal queries — EXACT over the full population,
    # no sampling. (Fixes the "300 of N" sampling problem for these chart types.)
    if plan.viz_type == VizType.bar_chart and facet_exec.can_facet_plan(plan.dimension, None, plan.metric):
        rows, total, notes = await facet_exec.faceted_categorical(
            client,
            plan.filters,
            plan.dimension,
            limit=plan.limit,
            sort_desc=plan.sort != "y_asc",
        )
        return build_response(plan, [], total, filters_applied, exact_rows=rows, exact_notes=notes)

    if plan.viz_type == VizType.grouped_bar and facet_exec.can_facet_plan(
        plan.dimension, plan.secondary_dimension, plan.metric
    ):
        rows, total, notes = await facet_exec.faceted_grouped(
            client, plan.filters, plan.dimension, plan.secondary_dimension, limit=plan.limit
        )
        return build_response(plan, [], total, filters_applied, exact_rows=rows, exact_notes=notes)

    # Record-fetch path (sampling) for high-cardinality, time, histogram, scatter,
    # network, geo. pageSize maxed at 1000 to pull a large, representative sample.
    max_records = request.max_records or _DEFAULT_MAX_RECORDS
    page_size = min(1000, max_records)
    params = params_for_plan(plan, page_size=page_size)
    studies, total = await client.search_studies(params, max_records=max_records)

    return build_response(plan, studies, total, filters_applied)


async def _cohort_record_fetch(
    request_client: CTGovClient, plan: QueryPlan, request: VisualizeRequest
) -> tuple[list[dict], int, int, list[str]]:
    """Fallback for cohort comparison over a non-facetable dimension: fetch records
    per cohort and aggregate. Returns (rows, total_population, fetched, notes)."""
    dim = plan.dimension or Dimension.phase
    max_records = request.max_records or _DEFAULT_MAX_RECORDS
    page_size = min(1000, max_records)

    rows: list[dict] = []
    total = 0
    fetched = 0
    sampled = False
    for cohort in plan.cohorts or []:
        cplan = plan.model_copy(deep=True)
        cplan.filters = facet_exec.merge_filters(plan.filters, cohort.filters)
        cplan.cohorts = None
        params = params_for_plan(cplan, page_size=page_size)
        studies, ctotal = await request_client.search_studies(params, max_records=max_records)
        total += ctotal
        fetched += len(studies)
        if len(studies) < ctotal:
            sampled = True
        crows, _ = agg.aggregate_categorical(studies, dim, plan.metric, "trial_count")
        for r in crows:
            r["series"] = cohort.label
            rows.append(r)

    labels = " vs ".join(c.label for c in (plan.cohorts or []))
    notes = [f"Comparing {labels} by {dim.value}."]
    if sampled:
        notes.append(
            "One or more cohorts exceeded the fetch limit; their counts reflect a "
            "sample of the most recent records, not the full population."
        )
    return rows, total, fetched, notes


def build_from_studies(request: VisualizeRequest, studies: list[dict], total: int) -> VisualizeResponse:
    """Synchronous path used by tests/fixtures: plan + provided studies -> response."""
    plan = plan_query(request)
    return build_response(plan, studies, total, _filters_applied(plan))
