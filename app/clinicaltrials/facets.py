"""Faceted exact-count support.

For bounded-enum dimensions we can get EXACT category counts by issuing one
``countTotal`` query per enum value (with a tiny pageSize to also grab example
trials for citations) — instead of sampling records and approximating. Bursts of
these queries run concurrently; ClinicalTrials.gov tolerates this comfortably.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import Dimension


@dataclass(frozen=True)
class FacetDef:
    area_field: str  # Essie AREA[...] field name
    values: list[str]  # enum raw values
    labels: dict[str, str]  # raw -> display label


_PHASE_LABELS = {
    "EARLY_PHASE1": "Early Phase 1",
    "PHASE1": "Phase 1",
    "PHASE2": "Phase 2",
    "PHASE3": "Phase 3",
    "PHASE4": "Phase 4",
    "NA": "Not Applicable",
}
_STATUS_LABELS = {
    "RECRUITING": "Recruiting",
    "NOT_YET_RECRUITING": "Not Yet Recruiting",
    "ENROLLING_BY_INVITATION": "Enrolling by Invitation",
    "ACTIVE_NOT_RECRUITING": "Active, Not Recruiting",
    "SUSPENDED": "Suspended",
    "TERMINATED": "Terminated",
    "COMPLETED": "Completed",
    "WITHDRAWN": "Withdrawn",
    "UNKNOWN": "Unknown",
}
_STUDY_TYPE_LABELS = {
    "INTERVENTIONAL": "Interventional",
    "OBSERVATIONAL": "Observational",
    "EXPANDED_ACCESS": "Expanded Access",
}
_SPONSOR_CLASS_LABELS = {
    "INDUSTRY": "Industry",
    "NIH": "NIH",
    "FED": "Federal",
    "OTHER_GOV": "Other Government",
    "NETWORK": "Network",
    "OTHER": "Other",
    "INDIV": "Individual",
    "UNKNOWN": "Unknown",
}

FACETABLE: dict[Dimension, FacetDef] = {
    Dimension.phase: FacetDef("Phase", list(_PHASE_LABELS), _PHASE_LABELS),
    Dimension.status: FacetDef("OverallStatus", list(_STATUS_LABELS), _STATUS_LABELS),
    Dimension.study_type: FacetDef("StudyType", list(_STUDY_TYPE_LABELS), _STUDY_TYPE_LABELS),
    Dimension.sponsor_class: FacetDef(
        "LeadSponsorClass", list(_SPONSOR_CLASS_LABELS), _SPONSOR_CLASS_LABELS
    ),
}

# Max number of facet queries we're willing to issue for one request (keeps even
# grouped 2-D facets — e.g. phase(6) x status(9) = 54 — fast and polite).
FACET_QUERY_BUDGET = 80


def is_facetable(dim: Dimension | None) -> bool:
    return dim in FACETABLE


def facet_values(dim: Dimension) -> list[tuple[str, str]]:
    """Return [(raw_value, label)] for the dimension's enum."""
    fd = FACETABLE[dim]
    return [(v, fd.labels.get(v, v)) for v in fd.values]


def area_expr(dim: Dimension, raw_value: str) -> str:
    return f"AREA[{FACETABLE[dim].area_field}]{raw_value}"


def field_path(dim: Dimension) -> str:
    """JSON path used in citations for this faceted dimension."""
    return {
        Dimension.phase: "protocolSection.designModule.phases",
        Dimension.status: "protocolSection.statusModule.overallStatus",
        Dimension.study_type: "protocolSection.designModule.studyType",
        Dimension.sponsor_class: "protocolSection.sponsorCollaboratorsModule.leadSponsor.class",
    }[dim]
