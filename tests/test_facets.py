import pytest

from app.clinicaltrials import facet_exec, facets
from app.clinicaltrials.client import CTGovClient
from app.schemas import Dimension, Filters, Metric


def test_facetable_dims():
    assert facets.is_facetable(Dimension.phase)
    assert facets.is_facetable(Dimension.status)
    assert not facets.is_facetable(Dimension.sponsor)  # high cardinality
    assert not facets.is_facetable(Dimension.condition)


def test_area_expr_and_field_path():
    assert facets.area_expr(Dimension.phase, "PHASE2") == "AREA[Phase]PHASE2"
    assert facets.area_expr(Dimension.status, "RECRUITING") == "AREA[OverallStatus]RECRUITING"
    assert facets.field_path(Dimension.phase) == "protocolSection.designModule.phases"


def test_can_facet_plan_routing():
    # single enum -> yes
    assert facet_exec.can_facet_plan(Dimension.phase, None, Metric.count)
    # high-cardinality -> no
    assert not facet_exec.can_facet_plan(Dimension.sponsor, None, Metric.count)
    # non-count metric -> no
    assert not facet_exec.can_facet_plan(Dimension.phase, None, Metric.enrollment_sum)
    # grouped enum x enum within budget -> yes (6 x 9 = 54 <= 80)
    assert facet_exec.can_facet_plan(Dimension.phase, Dimension.status, Metric.count)
    # grouped with a high-cardinality secondary -> no
    assert not facet_exec.can_facet_plan(Dimension.phase, Dimension.sponsor, Metric.count)


@pytest.mark.asyncio
async def test_faceted_categorical_builds_exact_rows(monkeypatch):
    # base total then per-phase counts (6 phases in enum order)
    results = [(1000, [])] + [
        (c, [{"protocolSection": {"identificationModule": {"nctId": f"NCT{c}"}}}])
        for c in (5, 200, 400, 90, 12, 60)  # early1, p1, p2, p3, p4, na
    ]

    async def fake_count_many(self, param_sets, sample=3):
        return results[: len(param_sets)]

    monkeypatch.setattr(CTGovClient, "count_many", fake_count_many)
    rows, total, notes = await facet_exec.faceted_categorical(
        CTGovClient(), Filters(condition="x"), Dimension.phase
    )
    assert total == 1000
    # sorted desc by count, exact values preserved, citations present
    assert rows[0]["trial_count"] == 400
    assert all(r["references"] for r in rows)
    assert any("Exact counts" in n for n in notes)


@pytest.mark.asyncio
async def test_faceted_grouped_drops_zero_combos(monkeypatch):
    # 6 phases x 9 statuses = 54 combos + 1 base = 55; make most zero
    n_combos = len(facets.FACETABLE[Dimension.phase].values) * len(
        facets.FACETABLE[Dimension.status].values
    )
    results = [(500, [])] + [(0, [])] * n_combos
    results[1] = (42, [{"protocolSection": {"identificationModule": {"nctId": "NCT42"}}}])

    async def fake_count_many(self, param_sets, sample=3):
        return results[: len(param_sets)]

    monkeypatch.setattr(CTGovClient, "count_many", fake_count_many)
    rows, total, _ = await facet_exec.faceted_grouped(
        CTGovClient(), Filters(condition="x"), Dimension.phase, Dimension.status
    )
    assert total == 500
    assert len(rows) == 1  # only the one non-zero combo
    assert rows[0]["trial_count"] == 42
