from app.agg import network as net
from app.schemas import EntityType


def test_network_builds_nodes_and_edges(pembro_studies):
    graph, _ = net.build_network(
        pembro_studies,
        [EntityType.drug, EntityType.condition],
        "drug-condition",
    )
    assert graph["nodes"], "expected entity nodes"
    assert graph["edges"], "expected co-occurrence edges"


def test_nodes_have_groups_and_citations(pembro_studies):
    graph, _ = net.build_network(
        pembro_studies, [EntityType.drug, EntityType.condition], "drug-condition"
    )
    groups = {n["group"] for n in graph["nodes"]}
    assert groups <= {"drug", "condition"}
    for n in graph["nodes"]:
        assert n["references"]
        assert n["weight"] >= 1


def test_edges_reference_real_trials_and_weight(pembro_studies):
    graph, _ = net.build_network(
        pembro_studies, [EntityType.drug, EntityType.condition], "drug-condition"
    )
    for e in graph["edges"]:
        assert e["weight"] >= 1
        assert e["weight"] == e["total_contributors"]
        assert e["references"][0]["nct_id"].startswith("NCT")
        # edge endpoints must be present in node set
    node_ids = {n["id"] for n in graph["nodes"]}
    for e in graph["edges"]:
        assert e["source"] in node_ids and e["target"] in node_ids


def test_edge_weight_equals_shared_trials():
    studies = [
        {
            "protocolSection": {
                "identificationModule": {"nctId": f"NCT{i}"},
                "armsInterventionsModule": {"interventions": [{"name": "DrugX", "type": "DRUG"}]},
                "conditionsModule": {"conditions": ["CondY"]},
            }
        }
        for i in range(3)
    ]
    graph, _ = net.build_network(studies, [EntityType.drug, EntityType.condition], "drug-condition")
    edge = graph["edges"][0]
    assert edge["weight"] == 3


def test_caps_respected(pembro_studies):
    graph, notes = net.build_network(
        pembro_studies,
        [EntityType.condition, EntityType.sponsor],
        "condition-sponsor",
        max_nodes=5,
        max_edges=5,
    )
    assert len(graph["nodes"]) <= 5
    assert len(graph["edges"]) <= 5
