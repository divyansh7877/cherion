"""Extract dimension values from a raw CT.gov study record.

Each extractor returns a list of ``(value, field_path, raw_value)`` tuples so the
aggregator can both group and build citations. A study may contribute multiple
values for a dimension (e.g. several conditions, several intervention types); for
single-valued dimensions the list has one entry.

``value`` is the normalized label used for grouping/display. ``raw_value`` is the
exact string from the API used in the citation.
"""

from __future__ import annotations

from app.schemas import Dimension

# Human-readable labels for CT.gov enums.
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

Triple = tuple[str, str, str]  # (label, field_path, raw_value)


def _proto(study: dict) -> dict:
    return study.get("protocolSection", {})


def nct_id(study: dict) -> str:
    return _proto(study).get("identificationModule", {}).get("nctId", "UNKNOWN")


def _phase(study: dict) -> list[Triple]:
    phases = _proto(study).get("designModule", {}).get("phases", [])
    if not phases:
        return [("Not Applicable", "protocolSection.designModule.phases", "NA")]
    return [(_PHASE_LABELS.get(p, p), "protocolSection.designModule.phases", p) for p in phases]


def _status(study: dict) -> list[Triple]:
    s = _proto(study).get("statusModule", {}).get("overallStatus")
    if not s:
        return []
    return [(_STATUS_LABELS.get(s, s), "protocolSection.statusModule.overallStatus", s)]


def _sponsor(study: dict) -> list[Triple]:
    name = _proto(study).get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name")
    if not name:
        return []
    return [(name, "protocolSection.sponsorCollaboratorsModule.leadSponsor.name", name)]


def _sponsor_class(study: dict) -> list[Triple]:
    cls = _proto(study).get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("class")
    if not cls:
        return []
    return [(cls, "protocolSection.sponsorCollaboratorsModule.leadSponsor.class", cls)]


def _study_type(study: dict) -> list[Triple]:
    t = _proto(study).get("designModule", {}).get("studyType")
    if not t:
        return []
    return [(t.title(), "protocolSection.designModule.studyType", t)]


def _start_year(study: dict) -> list[Triple]:
    date = _proto(study).get("statusModule", {}).get("startDateStruct", {}).get("date")
    if not date:
        return []
    year = date[:4]
    if not year.isdigit():
        return []
    return [(year, "protocolSection.statusModule.startDateStruct.date", date)]


def _condition(study: dict) -> list[Triple]:
    conds = _proto(study).get("conditionsModule", {}).get("conditions", [])
    return [(c, "protocolSection.conditionsModule.conditions", c) for c in conds]


def _intervention(study: dict) -> list[Triple]:
    intrs = _proto(study).get("armsInterventionsModule", {}).get("interventions", [])
    out: list[Triple] = []
    for it in intrs:
        name = it.get("name")
        if name:
            out.append((name, "protocolSection.armsInterventionsModule.interventions.name", name))
    return out


def _intervention_type(study: dict) -> list[Triple]:
    intrs = _proto(study).get("armsInterventionsModule", {}).get("interventions", [])
    seen: set[str] = set()
    out: list[Triple] = []
    for it in intrs:
        t = it.get("type")
        if t and t not in seen:
            seen.add(t)
            out.append((t.title(), "protocolSection.armsInterventionsModule.interventions.type", t))
    return out


_DISPATCH = {
    Dimension.phase: _phase,
    Dimension.status: _status,
    Dimension.sponsor: _sponsor,
    Dimension.sponsor_class: _sponsor_class,
    Dimension.study_type: _study_type,
    Dimension.start_year: _start_year,
    Dimension.condition: _condition,
    Dimension.intervention: _intervention,
    Dimension.intervention_type: _intervention_type,
}


def extract_dimension(study: dict, dim: Dimension) -> list[Triple]:
    """Return all (label, field_path, raw_value) triples for a dimension."""
    fn = _DISPATCH.get(dim)
    return fn(study) if fn else []


def enrollment_count(study: dict) -> int | None:
    """Numeric enrollment, used for histogram/scatter axes and enrollment metrics."""
    info = _proto(study).get("designModule", {}).get("enrollmentInfo", {})
    val = info.get("count")
    return int(val) if isinstance(val, (int, float)) else None


def duration_days(study: dict) -> int | None:
    """Study duration in days from start to (primary) completion, for scatter."""
    sm = _proto(study).get("statusModule", {})
    start = sm.get("startDateStruct", {}).get("date")
    end = sm.get("completionDateStruct", {}).get("date") or sm.get("primaryCompletionDateStruct", {}).get("date")
    if not start or not end:
        return None
    from datetime import date

    def _parse(d: str) -> date | None:
        parts = d.split("-")
        try:
            y = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return date(y, m, day)
        except (ValueError, IndexError):
            return None

    s, e = _parse(start), _parse(end)
    if not s or not e:
        return None
    return (e - s).days
