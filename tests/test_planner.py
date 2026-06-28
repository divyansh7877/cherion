from app.planner import _heuristic_plan, repair_plan
from app.schemas import (
    Dimension,
    EntityType,
    Filters,
    Metric,
    NetworkSpec,
    QueryPlan,
    VizType,
)


def test_heuristic_picks_geo_for_where_query():
    plan = _heuristic_plan("where are recruiting alzheimer trials located")
    assert plan.viz_type == VizType.geo_map
    assert "RECRUITING" in plan.filters.status


def test_heuristic_time_series():
    plan = _heuristic_plan("number of diabetes trials each year since 2015")
    assert plan.viz_type == VizType.time_series
    assert plan.filters.start_year == 2015


def test_heuristic_network():
    plan = _heuristic_plan("network of drugs and conditions")
    assert plan.viz_type == VizType.network_graph
    assert plan.network is not None


def test_repair_grouped_bar_fills_dimensions():
    plan = QueryPlan(viz_type=VizType.grouped_bar)
    repaired = repair_plan(plan)
    assert repaired.dimension is not None
    assert repaired.secondary_dimension is not None


def test_repair_time_series_forces_year_dimension():
    plan = QueryPlan(viz_type=VizType.time_series, dimension=Dimension.phase)
    assert repair_plan(plan).dimension == Dimension.start_year


def test_repair_bar_over_enrollment_becomes_histogram():
    plan = QueryPlan(viz_type=VizType.bar_chart, dimension=Dimension.enrollment)
    assert repair_plan(plan).viz_type == VizType.histogram


def test_repair_network_defaults_node_types():
    plan = QueryPlan(viz_type=VizType.network_graph)
    repaired = repair_plan(plan)
    assert len(repaired.network.node_types) >= 2
    assert repaired.network.edge_relation


def test_repair_filters_invalid_enums():
    plan = QueryPlan(
        viz_type=VizType.bar_chart,
        dimension=Dimension.phase,
        filters=Filters(phase=["PHASE2", "BOGUS"], status=["RECRUITING", "NOPE"]),
    )
    repaired = repair_plan(plan)
    assert repaired.filters.phase == ["PHASE2"]
    assert repaired.filters.status == ["RECRUITING"]


def test_repair_enrollment_metric_demoted_for_histogram():
    plan = QueryPlan(viz_type=VizType.histogram, metric=Metric.enrollment_avg)
    assert repair_plan(plan).metric == Metric.count


def test_network_edge_relation_inferred_from_node_types():
    plan = QueryPlan(
        viz_type=VizType.network_graph,
        network=NetworkSpec(node_types=[EntityType.sponsor, EntityType.condition]),
    )
    assert repair_plan(plan).network.edge_relation == "sponsor-condition"
