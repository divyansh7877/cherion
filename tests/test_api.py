"""End-to-end tests for the pipeline and FastAPI endpoint with a mocked CT.gov client."""

import pytest
from fastapi.testclient import TestClient

from app.clinicaltrials.client import CTGovClient
from app.main import app
from app.pipeline import build_from_studies
from app.schemas import VisualizeRequest, VizType


def test_health():
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


def test_bar_chart_end_to_end(pembro_studies):
    req = VisualizeRequest(query="trials by phase for pembrolizumab")
    resp = build_from_studies(req, pembro_studies, total=2890)
    assert resp.visualization.type == VizType.bar_chart
    assert resp.visualization.encoding.x.field == "phase"
    assert resp.visualization.encoding.y.field == "trial_count"
    assert resp.visualization.data
    assert resp.meta.total_matching_trials == 2890
    assert resp.meta.trials_aggregated == len(pembro_studies)
    # sampling warning since fetched < total
    assert resp.meta.warnings


def test_every_datum_has_citations(pembro_studies):
    req = VisualizeRequest(query="trials by sponsor", sponsor=None)
    resp = build_from_studies(req, pembro_studies, total=len(pembro_studies))
    for row in resp.visualization.data:
        assert row["references"]


def test_geo_end_to_end(diabetes_studies):
    req = VisualizeRequest(query="where are diabetes trials located by country")
    resp = build_from_studies(req, diabetes_studies, total=len(diabetes_studies))
    assert resp.visualization.type == VizType.geo_map
    assert "regions" in resp.visualization.data


def test_network_end_to_end(pembro_studies):
    req = VisualizeRequest(query="network of drugs and conditions for pembrolizumab")
    resp = build_from_studies(req, pembro_studies, total=len(pembro_studies))
    assert resp.visualization.type == VizType.network_graph
    assert resp.visualization.data["nodes"]
    assert resp.visualization.data["edges"]


def test_response_is_json_serializable(pembro_studies):
    req = VisualizeRequest(query="trials by phase")
    resp = build_from_studies(req, pembro_studies, total=len(pembro_studies))
    # model_dump_json must not raise
    assert resp.model_dump_json()


@pytest.mark.asyncio
async def test_pipeline_faceted_bar_with_mocked_client(monkeypatch):
    """Bar over phase (enum) takes the faceted exact path -> count_many, not search."""
    from app import pipeline

    # one base-total result + one per phase value (6 phases)
    fake_results = [(2890, [])] + [
        (n, [{"protocolSection": {"identificationModule": {"nctId": f"NCT{n}"}}}])
        for n in (3, 75, 120, 28, 10, 2)
    ]

    async def fake_count_many(self, param_sets, sample=3):
        return fake_results[: len(param_sets)]

    monkeypatch.setattr(CTGovClient, "count_many", fake_count_many)
    req = VisualizeRequest(query="trials by phase for pembrolizumab")
    resp = await pipeline.run_pipeline(req)
    assert resp.visualization.type == VizType.bar_chart
    assert resp.meta.total_matching_trials == 2890
    # exact path: aggregated == full population, no sampling warning
    assert resp.meta.trials_aggregated == 2890
    assert not resp.meta.warnings
    assert all(r["references"] for r in resp.visualization.data)


@pytest.mark.asyncio
async def test_pipeline_sampling_path_with_mocked_client(monkeypatch, diabetes_studies):
    """Geo (high-cardinality) takes the record-fetch sampling path -> search_studies."""
    from app import pipeline

    async def fake_search(self, params, max_records=1000, max_pages=10):
        return diabetes_studies, 24010

    monkeypatch.setattr(CTGovClient, "search_studies", fake_search)
    req = VisualizeRequest(query="where are diabetes trials located by country")
    resp = await pipeline.run_pipeline(req)
    assert resp.visualization.type == VizType.geo_map
    assert resp.meta.total_matching_trials == 24010
    assert resp.meta.warnings  # sampled
