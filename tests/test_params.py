from app.clinicaltrials.params import fields_for_plan, params_for_plan
from app.schemas import Dimension, Filters, NetworkSpec, EntityType, QueryPlan, VizType


def test_histogram_requests_design_module():
    plan = QueryPlan(viz_type=VizType.histogram)
    assert "protocolSection.designModule" in fields_for_plan(plan)


def test_scatter_requests_design_module():
    plan = QueryPlan(viz_type=VizType.scatter_plot)
    assert "protocolSection.designModule" in fields_for_plan(plan)


def test_geo_requests_locations():
    plan = QueryPlan(viz_type=VizType.geo_map)
    assert "protocolSection.contactsLocationsModule" in fields_for_plan(plan)


def test_network_requests_entity_modules():
    plan = QueryPlan(
        viz_type=VizType.network_graph,
        network=NetworkSpec(node_types=[EntityType.drug, EntityType.sponsor]),
    )
    fields = fields_for_plan(plan)
    assert "protocolSection.armsInterventionsModule" in fields
    assert "protocolSection.sponsorCollaboratorsModule" in fields


def test_params_maps_filters_to_ctgov():
    plan = QueryPlan(
        viz_type=VizType.bar_chart,
        dimension=Dimension.phase,
        filters=Filters(
            drug_name="pembrolizumab",
            condition="lung cancer",
            phase=["PHASE2"],
            status=["RECRUITING"],
            start_year=2018,
            end_year=2022,
        ),
    )
    p = params_for_plan(plan)
    assert p["query.intr"] == "pembrolizumab"
    assert p["query.cond"] == "lung cancer"
    # phase has NO dedicated filter param — it must go through AREA[Phase].
    assert "filter.phase" not in p
    assert "AREA[Phase]PHASE2" in p["filter.advanced"]
    assert p["filter.overallStatus"] == "RECRUITING"
    assert "RANGE[2018-01-01,2022-12-31]" in p["filter.advanced"]
    assert p["countTotal"] == "true"


def test_multiple_phases_use_or_expression():
    plan = QueryPlan(
        viz_type=VizType.bar_chart,
        dimension=Dimension.status,
        filters=Filters(phase=["PHASE2", "PHASE3"]),
    )
    p = params_for_plan(plan)
    assert "AREA[Phase](PHASE2 OR PHASE3)" in p["filter.advanced"]
