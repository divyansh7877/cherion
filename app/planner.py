"""LLM planner: natural-language query -> QueryPlan, via Anthropic forced tool-use.

The LLM's ONLY job is to fill the QueryPlan IR. It never sees or emits data
points. The repair layer then merges explicit request overrides and clamps any
illegal field combinations so the executor always receives a runnable plan.
"""

from __future__ import annotations

import os

from app.schemas import (
    PHASES,
    STATUSES,
    Cohort,
    Dimension,
    EntityType,
    Filters,
    Metric,
    NetworkSpec,
    QueryPlan,
    VisualizeRequest,
    VizType,
)

_PLANNER_MODEL = os.environ.get("CHERION_MODEL", "claude-sonnet-4-6")

_SYSTEM = """You are a query planner for a clinical-trials visualization service.
Convert the user's natural-language question into a structured QueryPlan by calling
the build_query_plan tool. You NEVER produce data, counts, or trial records — only
the plan describing how to fetch and shape them.

Guidance:
- Pick the viz_type that best answers the question:
  - bar_chart: counts grouped by one category (phase, status, sponsor, condition, country...).
  - grouped_bar: counts split by TWO categories (set dimension and secondary_dimension).
  - time_series: trend over time (set dimension=start_year, choose time_granularity).
  - histogram: distribution of a numeric value (enrollment size).
  - scatter_plot: relationship between two numerics (enrollment vs duration).
  - network_graph: relationships/co-occurrence between entities (drugs, conditions,
    sponsors, sites). Set network.node_types and network.edge_relation like "drug-condition".
  - geo_map: geographic distribution by country/location.
- COMPARISONS ("A vs B", "compare X and Y", "X versus Y"): use `cohorts` — a list of
  named groups, one per thing being compared. Each cohort has a `label` and its own
  `filters`. Set `dimension` to what you break the comparison down BY (phase by default,
  or status/study_type/sponsor_class). Put SHARED constraints in the top-level `filters`
  and the DIFFERING constraint in each cohort. Leave secondary_dimension unset.
  Example — "Compare phases for Aspirin vs Clopidogrel":
    dimension=phase, cohorts=[{label:"Aspirin", filters:{drug_name:"Aspirin"}},
    {label:"Clopidogrel", filters:{drug_name:"Clopidogrel"}}].
  Example — "Compare recruiting status of Pfizer vs Moderna trials":
    dimension=status, cohorts=[{label:"Pfizer", filters:{sponsor:"Pfizer"}},
    {label:"Moderna", filters:{sponsor:"Moderna"}}].
- Put search constraints in filters (drug_name, condition, sponsor, country, phase[],
  status[], start_year, end_year, term).
- Use CT.gov enums exactly. Phases: EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4, NA.
  Statuses: RECRUITING, NOT_YET_RECRUITING, ENROLLING_BY_INVITATION, ACTIVE_NOT_RECRUITING,
  SUSPENDED, TERMINATED, COMPLETED, WITHDRAWN, UNKNOWN.
- Always write a one-sentence `interpretation` of how you understood the query.
"""


def _tool_schema() -> dict:
    schema = QueryPlan.model_json_schema()
    return {
        "name": "build_query_plan",
        "description": "Emit the structured plan for fetching and visualizing clinical-trial data.",
        "input_schema": schema,
    }


def plan_query(request: VisualizeRequest) -> QueryPlan:
    """Produce a QueryPlan for the request (LLM plan + overrides + repair)."""
    plan = _llm_plan(request.query)
    plan = _apply_overrides(plan, request)
    plan = repair_plan(plan)
    return plan


def _llm_plan(query: str) -> QueryPlan:
    """Call Anthropic with forced tool-use. Falls back to a heuristic plan if no
    API key is configured OR the call fails (keeps the service usable offline and
    resilient to auth/network/validation errors — it always returns a runnable plan)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _heuristic_plan(query)

    try:
        from anthropic import Anthropic

        client = Anthropic()
        tool = _tool_schema()
        msg = client.messages.create(
            model=_PLANNER_MODEL,
            max_tokens=1024,
            system=_SYSTEM,
            tools=[tool],
            tool_choice={"type": "tool", "name": "build_query_plan"},
            messages=[{"role": "user", "content": query}],
        )
        for block in msg.content:
            if block.type == "tool_use" and block.name == "build_query_plan":
                return QueryPlan.model_validate(block.input)
    except Exception:
        # Auth error (bad/placeholder key), network failure, or schema mismatch:
        # degrade to the heuristic rather than failing the request.
        return _heuristic_plan(query)
    # Should not happen with forced tool_choice; fall back defensively.
    return _heuristic_plan(query)


def _apply_overrides(plan: QueryPlan, request: VisualizeRequest) -> QueryPlan:
    """Explicit request params win over the LLM's interpretation."""
    f: Filters = plan.filters
    if request.drug_name is not None:
        f.drug_name = request.drug_name
    if request.condition is not None:
        f.condition = request.condition
    if request.sponsor is not None:
        f.sponsor = request.sponsor
    if request.country is not None:
        f.country = request.country
    if request.trial_phase:
        f.phase = request.trial_phase
    if request.status:
        f.status = request.status
    if request.start_year is not None:
        f.start_year = request.start_year
    if request.end_year is not None:
        f.end_year = request.end_year
    return plan


def _cohort_has_filter(cohort: Cohort) -> bool:
    """A cohort only earns a series if it actually narrows the population."""
    f = cohort.filters
    return any([f.drug_name, f.condition, f.sponsor, f.country, f.term, f.phase, f.status, f.start_year, f.end_year])


def repair_plan(plan: QueryPlan) -> QueryPlan:
    """Clamp illegal combinations so the executor always gets a runnable plan."""
    # Validate enums in filters (top-level and per-cohort).
    plan.filters.phase = [p for p in plan.filters.phase if p in PHASES]
    plan.filters.status = [s for s in plan.filters.status if s in STATUSES]

    # Comparison cohorts: an 'A vs B' question becomes a grouped bar with one
    # series per cohort, split by `dimension`. Needs >= 2 well-formed cohorts.
    if plan.cohorts is not None:
        valid = [c for c in plan.cohorts if c.label and _cohort_has_filter(c)]
        for c in valid:
            c.filters.phase = [p for p in c.filters.phase if p in PHASES]
            c.filters.status = [s for s in c.filters.status if s in STATUSES]
        if len(valid) >= 2:
            plan.cohorts = valid
            plan.viz_type = VizType.grouped_bar
            plan.secondary_dimension = None
            # Cohorts are compared over a facetable enum; phase is the sane default.
            if plan.dimension is None or plan.dimension == Dimension.enrollment:
                plan.dimension = Dimension.phase
        else:
            plan.cohorts = None

    if plan.viz_type == VizType.grouped_bar:
        if plan.dimension is None:
            plan.dimension = Dimension.phase
        # Without cohorts a grouped bar needs a second categorical dimension.
        if plan.secondary_dimension is None and not plan.cohorts:
            plan.secondary_dimension = Dimension.status

    elif plan.viz_type == VizType.time_series:
        plan.dimension = Dimension.start_year

    elif plan.viz_type in (VizType.bar_chart,):
        if plan.dimension is None:
            plan.dimension = Dimension.phase
        # enrollment is numeric; a bar over it makes no sense -> histogram.
        if plan.dimension == Dimension.enrollment:
            plan.viz_type = VizType.histogram

    elif plan.viz_type == VizType.network_graph:
        if plan.network is None or len(plan.network.node_types) < 2:
            plan.network = NetworkSpec(
                node_types=[EntityType.drug, EntityType.condition],
                edge_relation="drug-condition",
            )
        if not plan.network.edge_relation:
            nt = plan.network.node_types
            plan.network.edge_relation = f"{nt[0].value}-{nt[1].value}"

    # enrollment metrics require a categorical dimension to group by.
    if plan.metric in (Metric.enrollment_sum, Metric.enrollment_avg):
        if plan.viz_type in (VizType.histogram, VizType.scatter_plot, VizType.network_graph):
            plan.metric = Metric.count

    return plan


# --------------------------------------------------------------------------- #
# Offline heuristic fallback (no API key) — keyword-based, best-effort.
# --------------------------------------------------------------------------- #


_COMPARE_STOP = {
    "compare",
    "comparing",
    "phases",
    "phase",
    "for",
    "of",
    "in",
    "trials",
    "studies",
    "involving",
    "between",
    "the",
    "show",
    "status",
    "study",
    "type",
    "types",
    "drug",
    "drugs",
    "sponsor",
    "sponsors",
    "condition",
    "conditions",
    "disease",
}


def _extract_comparison(query: str) -> tuple[str, str] | None:
    """Best-effort 'A vs B' entity extraction for the offline heuristic."""
    import re

    m = re.search(
        r"([A-Za-z0-9][\w\- ]*?)\s+(?:vs\.?|versus)\s+([A-Za-z0-9][\w\- ]*)",
        query,
        re.IGNORECASE,
    )
    if not m:
        return None

    def _left(s: str) -> str:
        # Keep the trailing run of entity words (stop at the connective before it).
        words = re.findall(r"[A-Za-z0-9\-]+", s)
        keep: list[str] = []
        for w in reversed(words):
            if w.lower() in _COMPARE_STOP and keep:
                break
            keep.append(w)
        keep.reverse()
        while keep and keep[0].lower() in _COMPARE_STOP:
            keep.pop(0)
        return " ".join(keep).strip()

    def _right(s: str) -> str:
        words = re.findall(r"[A-Za-z0-9\-]+", s)
        out: list[str] = []
        for w in words:
            if w.lower() in {"trials", "studies", "grouped", "over", "across", "by"} and out:
                break
            out.append(w)
        cleaned = [w for w in out if w.lower() not in _COMPARE_STOP]
        return " ".join(cleaned or out).strip()

    a, b = _left(m.group(1)), _right(m.group(2))
    return (a, b) if a and b else None


def _heuristic_plan(query: str) -> QueryPlan:
    import re

    q = query.lower()
    filters = Filters()

    # crude entity hints
    for kw, phase in [("phase 1", "PHASE1"), ("phase 2", "PHASE2"), ("phase 3", "PHASE3")]:
        if kw in q:
            filters.phase.append(phase)
    if "recruiting" in q:
        filters.status.append("RECRUITING")

    # comparison ("A vs B") -> cohort grouped bar (mirrors the LLM cohorts path).
    comp = _extract_comparison(query)
    if comp:
        a, b = comp

        def _mk(v: str) -> Filters:
            if "sponsor" in q:
                return Filters(sponsor=v)
            if "condition" in q or "disease" in q:
                return Filters(condition=v)
            return Filters(drug_name=v)

        if "status" in q:
            dim = Dimension.status
        elif "study type" in q:
            dim = Dimension.study_type
        else:
            dim = Dimension.phase
        return QueryPlan(
            viz_type=VizType.grouped_bar,
            dimension=dim,
            cohorts=[Cohort(label=a, filters=_mk(a)), Cohort(label=b, filters=_mk(b))],
            filters=filters,
            interpretation=f"Heuristic plan: comparing {a} vs {b} by {dim.value}.",
        )

    # crude topic extraction: text after "for"/"about" becomes a free-text term.
    # ("of"/"on" are too noisy — they precede things like "of enrollment size").
    _NON_TOPIC = {
        "enrollment",
        "size",
        "trials",
        "studies",
        "trial",
        "study",
        "number",
        "distribution",
        "phase",
        "status",
        "sponsor",
        "sponsors",
    }
    m = re.search(r"\b(?:for|about)\s+([a-z0-9][a-z0-9 \-]{2,40})", q)
    if m:
        term = m.group(1).strip()
        # drop trailing instruction words
        for stop in [" by ", " over ", " grouped", " across", " each", " per ", " started"]:
            term = term.split(stop)[0]
        term = term.strip()
        # ignore terms that are just chart/metric vocabulary, not a topic
        if term and not all(w in _NON_TOPIC for w in term.split()):
            filters.term = term
    years = [int(y) for y in re.findall(r"\b(?:19|20)\d{2}\b", query)]
    if years:
        filters.start_year = min(years)

    if any(w in q for w in ["where", "country", "countries", "location", "map", "geographic"]):
        viz, dim = VizType.geo_map, Dimension.country
    elif any(w in q for w in ["network", "co-occur", "relationship", "connected"]):
        return QueryPlan(
            viz_type=VizType.network_graph,
            network=NetworkSpec(
                node_types=[EntityType.drug, EntityType.condition],
                edge_relation="drug-condition",
            ),
            filters=filters,
            interpretation=f"Heuristic plan: network graph for '{query}'.",
        )
    elif any(w in q for w in ["over time", "trend", "each year", "by year", "timeline"]):
        viz, dim = VizType.time_series, Dimension.start_year
    elif "scatter" in q or ("enrollment" in q and ("vs" in q or "versus" in q or "duration" in q)):
        return QueryPlan(
            viz_type=VizType.scatter_plot,
            filters=filters,
            interpretation=f"Heuristic plan: enrollment vs duration scatter for '{query}'.",
        )
    elif any(w in q for w in ["distribution", "histogram", "enrollment size"]):
        return QueryPlan(
            viz_type=VizType.histogram,
            filters=filters,
            interpretation=f"Heuristic plan: enrollment histogram for '{query}'.",
        )
    elif "sponsor" in q:
        viz, dim = VizType.bar_chart, Dimension.sponsor
    elif "status" in q:
        viz, dim = VizType.bar_chart, Dimension.status
    elif "condition" in q or "disease" in q:
        viz, dim = VizType.bar_chart, Dimension.condition
    else:
        viz, dim = VizType.bar_chart, Dimension.phase

    return QueryPlan(
        viz_type=viz,
        dimension=dim,
        filters=filters,
        interpretation=f"Heuristic plan: {viz.value} by {dim.value} for '{query}'.",
    )
