"""Map a ``QueryPlan`` to ClinicalTrials.gov ``/studies`` query parameters and
decide which ``fields`` (modules) to request.

Keeping this pure and separate makes it trivial to unit-test the plan->params
translation without any network calls.
"""

from __future__ import annotations

from app.schemas import Dimension, QueryPlan, VizType

# Module field paths we may need, keyed by purpose. We always fetch identification
# + status (for NCT id and dates/citations); the rest are added based on the plan.
_BASE_FIELDS = [
    "protocolSection.identificationModule",
    "protocolSection.statusModule",
]

_DIMENSION_FIELDS: dict[Dimension, list[str]] = {
    Dimension.phase: ["protocolSection.designModule"],
    Dimension.status: ["protocolSection.statusModule"],
    Dimension.sponsor: ["protocolSection.sponsorCollaboratorsModule"],
    Dimension.sponsor_class: ["protocolSection.sponsorCollaboratorsModule"],
    Dimension.country: ["protocolSection.contactsLocationsModule"],
    Dimension.start_year: ["protocolSection.statusModule"],
    Dimension.study_type: ["protocolSection.designModule"],
    Dimension.intervention: ["protocolSection.armsInterventionsModule"],
    Dimension.intervention_type: ["protocolSection.armsInterventionsModule"],
    Dimension.condition: ["protocolSection.conditionsModule"],
    Dimension.enrollment: ["protocolSection.designModule"],
}

_ENTITY_FIELDS = {
    "drug": "protocolSection.armsInterventionsModule",
    "condition": "protocolSection.conditionsModule",
    "sponsor": "protocolSection.sponsorCollaboratorsModule",
    "site": "protocolSection.contactsLocationsModule",
}


def fields_for_plan(plan: QueryPlan) -> list[str]:
    """Return the minimal set of module field paths needed to satisfy the plan."""
    fields = list(_BASE_FIELDS)

    def add(paths: list[str]) -> None:
        for p in paths:
            if p not in fields:
                fields.append(p)

    for dim in (plan.dimension, plan.secondary_dimension):
        if dim is not None:
            add(_DIMENSION_FIELDS.get(dim, []))

    if plan.metric.value.startswith("enrollment"):
        add(["protocolSection.designModule"])

    # Histogram bins enrollment; scatter needs enrollment + dates (statusModule is base).
    if plan.viz_type in (VizType.histogram, VizType.scatter_plot):
        add(["protocolSection.designModule"])

    if plan.viz_type == VizType.geo_map:
        add(["protocolSection.contactsLocationsModule"])

    if plan.viz_type == VizType.network_graph and plan.network:
        for nt in plan.network.node_types:
            path = _ENTITY_FIELDS.get(nt.value)
            if path:
                add([path])

    return fields


def search_params(filters) -> tuple[dict[str, str], list[str]]:
    """Build the search constraints from filters: returns (params, advanced_exprs).

    ``params`` holds query.* + filter.overallStatus; ``advanced_exprs`` are the
    AREA[...] fragments to be AND-ed into filter.advanced. Faceting reuses this
    and appends its own AREA constraint before joining.
    """
    f = filters
    params: dict[str, str] = {}
    if f.condition:
        params["query.cond"] = f.condition
    if f.drug_name:
        params["query.intr"] = f.drug_name
    if f.sponsor:
        params["query.spons"] = f.sponsor
    if f.country:
        params["query.locn"] = f.country
    if f.term:
        params["query.term"] = f.term
    if f.status:
        params["filter.overallStatus"] = ",".join(f.status)

    # NOTE: there is no `filter.phase` param — phase must use AREA[Phase].
    advanced: list[str] = []
    if f.phase:
        phases = " OR ".join(f.phase)
        advanced.append(f"AREA[Phase]({phases})" if len(f.phase) > 1 else f"AREA[Phase]{f.phase[0]}")
    if f.start_year or f.end_year:
        lo = f"{f.start_year}-01-01" if f.start_year else "MIN"
        hi = f"{f.end_year}-12-31" if f.end_year else "MAX"
        advanced.append(f"AREA[StartDate]RANGE[{lo},{hi}]")
    return params, advanced


def params_for_plan(plan: QueryPlan, page_size: int = 200) -> dict[str, str]:
    """Build the query/filter params dict for ``GET /studies`` (record-fetch path)."""
    params, advanced = search_params(plan.filters)
    params.update(
        {
            "countTotal": "true",
            "pageSize": str(page_size),
            "fields": "|".join(fields_for_plan(plan)),
        }
    )
    if advanced:
        params["filter.advanced"] = " AND ".join(advanced)
    return params
