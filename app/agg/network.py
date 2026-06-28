"""Co-occurrence network builder.

Nodes are entities (drug, condition, sponsor, site). An edge connects two entities
that co-occur within the same trial; its weight is the number of shared trials.
Each node and edge carries citations to the contributing trials.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import product

from app.agg import extractors as ex
from app.agg.citations import build_references
from app.schemas import EntityType

def _site_extractor(study: dict) -> list[tuple[str, str, str]]:
    locs = (
        study.get("protocolSection", {})
        .get("contactsLocationsModule", {})
        .get("locations", [])
    )
    out, seen = [], set()
    for loc in locs:
        name = loc.get("facility") or loc.get("city")
        if name and name not in seen:
            seen.add(name)
            out.append((name, "protocolSection.contactsLocationsModule.locations.facility", name))
    return out


# entity type -> extractor returning [(label, field, raw_value)]
_ENTITY_EXTRACTORS = {
    EntityType.drug: ex._intervention,
    EntityType.condition: ex._condition,
    EntityType.sponsor: ex._sponsor,
    EntityType.site: _site_extractor,
}


def _parse_relation(edge_relation: str | None) -> tuple[EntityType, EntityType] | None:
    if not edge_relation or "-" not in edge_relation:
        return None
    a, b = edge_relation.split("-", 1)
    try:
        return EntityType(a.strip()), EntityType(b.strip())
    except ValueError:
        return None


def build_network(
    studies: list[dict],
    node_types: list[EntityType],
    edge_relation: str | None,
    max_nodes: int = 60,
    max_edges: int = 150,
) -> tuple[dict, list[str]]:
    """Build {nodes, edges}. Edges connect the two entity types in edge_relation
    (defaults to the first two node_types). Returns (graph, notes)."""
    notes: list[str] = []
    rel = _parse_relation(edge_relation)
    if rel is None and len(node_types) >= 2:
        rel = (node_types[0], node_types[1])
    if rel is None:
        return {"nodes": [], "edges": []}, ["Need two entity types to build a network."]

    type_a, type_b = rel
    node_refs: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
    node_weight: dict[tuple[str, str], int] = defaultdict(int)
    edge_refs: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)

    for study in studies:
        nct = ex.nct_id(study)
        a_vals = _ENTITY_EXTRACTORS[type_a](study)
        b_vals = _ENTITY_EXTRACTORS[type_b](study)
        a_seen = {(type_a.value, lbl) for lbl, _, _ in a_vals}
        b_seen = {(type_b.value, lbl) for lbl, _, _ in b_vals}
        for grp, lbl in a_seen:
            node_weight[(grp, lbl)] += 1
        for grp, lbl in b_seen:
            node_weight[(grp, lbl)] += 1
        for (la, fa, ra), (lb, _fb, _rb) in product(a_vals, b_vals):
            if type_a == type_b and la == lb:
                continue
            key = tuple(sorted([f"{type_a.value}:{la}", f"{type_b.value}:{lb}"]))
            edge_refs[key].append((nct, fa, ra))
            node_refs[(type_a.value, la)].append((nct, fa, ra))
            node_refs[(type_b.value, lb)].append((nct, _fb, _rb))

    # Build edges sorted by weight (shared trials).
    edge_items = sorted(edge_refs.items(), key=lambda kv: len(kv[1]), reverse=True)
    if len(edge_items) > max_edges:
        notes.append(f"Showing top {max_edges} of {len(edge_items)} edges by weight.")
        edge_items = edge_items[:max_edges]

    used_nodes: set[str] = set()
    edges = []
    for (src, tgt), contribs in edge_items:
        used_nodes.add(src)
        used_nodes.add(tgt)
        edges.append(
            {
                "source": src,
                "target": tgt,
                "weight": len(contribs),
                "total_contributors": len(contribs),
                "references": [r.model_dump() for r in build_references(contribs)],
            }
        )

    nodes = []
    for node_id in used_nodes:
        group, _, label = node_id.partition(":")
        contribs = node_refs.get((group, label), [])
        nodes.append(
            {
                "id": node_id,
                "label": label,
                "group": group,
                "weight": node_weight.get((group, label), len(contribs)),
                "total_contributors": len(contribs),
                "references": [r.model_dump() for r in build_references(contribs)],
            }
        )
    nodes.sort(key=lambda n: n["weight"], reverse=True)
    if len(nodes) > max_nodes:
        notes.append(f"Showing top {max_nodes} of {len(nodes)} nodes by weight.")
        keep = {n["id"] for n in nodes[:max_nodes]}
        nodes = nodes[:max_nodes]
        edges = [e for e in edges if e["source"] in keep and e["target"] in keep]

    return {"nodes": nodes, "edges": edges}, notes
