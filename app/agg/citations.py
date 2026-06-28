"""Build deep citations for aggregated data points.

A citation ties a datum back to a real trial record: nct_id + the exact field
path and value that contributed. Because aggregation runs over real records, we
collect contributors as a side effect of grouping and cap them here.
"""

from __future__ import annotations

from app.schemas import Reference

MAX_REFS_PER_DATUM = 5


def build_references(contributors: list[tuple[str, str, str]]) -> list[Reference]:
    """Convert (nct_id, field, value) contributor tuples into capped References."""
    refs = [
        Reference(nct_id=nct, field=field, value=value)
        for nct, field, value in contributors[:MAX_REFS_PER_DATUM]
    ]
    return refs
