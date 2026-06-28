"""Orchestration: request -> plan -> fetch -> aggregate -> spec.

The single coherent path every query flows through, regardless of type.
"""

from __future__ import annotations

from app.clinicaltrials import facet_exec
from app.clinicaltrials.client import CTGovClient
from app.clinicaltrials.params import params_for_plan
from app.planner import plan_query
from app.schemas import QueryPlan, VisualizeRequest, VisualizeResponse, VizType
from app.spec_builder import build_response

_DEFAULT_MAX_RECORDS = 1000


def _filters_applied(plan: QueryPlan) -> dict:
    return {k: v for k, v in plan.filters.model_dump().items() if v not in (None, [], "")}


async def run_pipeline(
    request: VisualizeRequest, client: CTGovClient | None = None
) -> VisualizeResponse:
    client = client or CTGovClient()
    plan = plan_query(request)
    filters_applied = _filters_applied(plan)

    # Fast exact path: count-based bar/grouped over bounded-enum dimensions are
    # computed via faceted countTotal queries — EXACT over the full population,
    # no sampling. (Fixes the "300 of N" sampling problem for these chart types.)
    if plan.viz_type == VizType.bar_chart and facet_exec.can_facet_plan(
        plan.dimension, None, plan.metric
    ):
        rows, total, notes = await facet_exec.faceted_categorical(
            client, plan.filters, plan.dimension, limit=plan.limit,
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


def build_from_studies(
    request: VisualizeRequest, studies: list[dict], total: int
) -> VisualizeResponse:
    """Synchronous path used by tests/fixtures: plan + provided studies -> response."""
    plan = plan_query(request)
    return build_response(plan, studies, total, _filters_applied(plan))
