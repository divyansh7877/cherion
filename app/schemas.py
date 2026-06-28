"""Pydantic models: the request, the LLM query-plan IR, and the response spec.

These models are the contract for the whole system. The ``QueryPlan`` is the
intermediate representation the LLM produces; everything downstream (API params,
aggregation, citations) is deterministic Python driven by it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------- #
# Controlled vocabularies (stable CT.gov enums + our viz vocabulary)
# --------------------------------------------------------------------------- #


class VizType(str, Enum):
    bar_chart = "bar_chart"
    grouped_bar = "grouped_bar"
    time_series = "time_series"
    histogram = "histogram"
    scatter_plot = "scatter_plot"
    network_graph = "network_graph"
    geo_map = "geo_map"


class Dimension(str, Enum):
    """A field a result set can be grouped/split by (the 'group by')."""

    phase = "phase"
    status = "status"
    sponsor = "sponsor"
    sponsor_class = "sponsor_class"
    country = "country"
    start_year = "start_year"
    study_type = "study_type"
    intervention = "intervention"
    intervention_type = "intervention_type"
    condition = "condition"
    enrollment = "enrollment"  # numeric — used for histogram/scatter axes


class Metric(str, Enum):
    count = "count"
    enrollment_sum = "enrollment_sum"
    enrollment_avg = "enrollment_avg"


class TimeGranularity(str, Enum):
    year = "year"
    month = "month"


class EntityType(str, Enum):
    drug = "drug"
    condition = "condition"
    sponsor = "sponsor"
    site = "site"


# CT.gov enum values, kept here so the planner/repair layer can validate against them.
PHASES = ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"]
STATUSES = [
    "RECRUITING",
    "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING",
    "SUSPENDED",
    "TERMINATED",
    "COMPLETED",
    "WITHDRAWN",
    "UNKNOWN",
]


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #


class Filters(BaseModel):
    """Structured filters. The planner fills these from the NL query; explicit
    request overrides are merged on top afterward (overrides win)."""

    drug_name: str | None = None
    condition: str | None = None
    sponsor: str | None = None
    country: str | None = None
    term: str | None = Field(None, description="Free-text Essie search across all fields")
    phase: list[str] = Field(default_factory=list, description="CT.gov phase enums")
    status: list[str] = Field(default_factory=list, description="CT.gov overallStatus enums")
    start_year: int | None = None
    end_year: int | None = None


class VisualizeRequest(BaseModel):
    """The service input. Only ``query`` is required; the rest are optional
    overrides that take precedence over the LLM's interpretation."""

    query: str = Field(..., description="Natural-language question about clinical trials")
    drug_name: str | None = None
    condition: str | None = None
    sponsor: str | None = None
    country: str | None = None
    trial_phase: list[str] | None = None
    status: list[str] | None = None
    start_year: int | None = None
    end_year: int | None = None
    max_records: int | None = Field(None, description="Cap on records fetched for aggregation")


# --------------------------------------------------------------------------- #
# The LLM intermediate representation (forced tool-use output)
# --------------------------------------------------------------------------- #


class NetworkSpec(BaseModel):
    node_types: list[EntityType] = Field(default_factory=list)
    edge_relation: str | None = Field(
        None, description="e.g. 'drug-condition', 'sponsor-condition', 'site-sponsor'"
    )


class QueryPlan(BaseModel):
    """The plan the LLM emits and the executor consumes. No data points here —
    only *how* to fetch and shape them."""

    viz_type: VizType
    dimension: Dimension | None = Field(None, description="Primary group-by / x-axis")
    secondary_dimension: Dimension | None = Field(None, description="Series / grouping / y-axis")
    metric: Metric = Metric.count
    filters: Filters = Field(default_factory=Filters)
    time_granularity: TimeGranularity = TimeGranularity.year
    network: NetworkSpec | None = None
    sort: str | None = Field(None, description="e.g. 'y_desc', 'x_asc'")
    limit: int | None = Field(None, description="Max categories/nodes to return")
    interpretation: str = Field(
        "", description="One-sentence restatement of how the query was understood"
    )


# --------------------------------------------------------------------------- #
# Output: visualization spec + meta
# --------------------------------------------------------------------------- #


class Reference(BaseModel):
    """A deep citation: an exact value from a real trial record backing a datum."""

    nct_id: str
    field: str = Field(..., description="JSON path in the CT.gov record, e.g. designModule.phases")
    value: str = Field(..., description="Exact field value/excerpt from the API response")


class Channel(BaseModel):
    """One visual-channel mapping (x, y, color, size, region, lat, lng...)."""

    field: str
    type: str = Field(..., description="nominal | ordinal | quantitative | temporal")
    title: str | None = None


class Encoding(BaseModel):
    """Channel mappings. Only the channels relevant to the viz type are set."""

    x: Channel | None = None
    y: Channel | None = None
    color: Channel | None = None
    size: Channel | None = None
    # geo
    region: Channel | None = None
    lat: Channel | None = None
    lng: Channel | None = None
    # network: declared as descriptors, the data lives under data.nodes/edges
    nodes: dict | None = None
    edges: dict | None = None


class Visualization(BaseModel):
    type: VizType
    title: str
    encoding: Encoding
    # For charts/geo: list of row dicts. For network: {"nodes": [...], "edges": [...]}.
    data: list[dict] | dict


class Meta(BaseModel):
    source: str = "clinicaltrials.gov"
    filters: dict = Field(default_factory=dict)
    query_interpretation: str = ""
    total_matching_trials: int | None = None
    trials_aggregated: int | None = None
    units: str | None = None
    sorting: str | None = None
    time_granularity: str | None = None
    grouping: str | None = None
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VisualizeResponse(BaseModel):
    visualization: Visualization
    meta: Meta
