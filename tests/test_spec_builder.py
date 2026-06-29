from app.schemas import Cohort, Dimension, Filters, QueryPlan, VizType
from app.spec_builder import build_response


def _cohort_plan():
    return QueryPlan(
        viz_type=VizType.grouped_bar,
        dimension=Dimension.phase,
        cohorts=[
            Cohort(label="Aspirin", filters=Filters(drug_name="Aspirin")),
            Cohort(label="Clopidogrel", filters=Filters(drug_name="Clopidogrel")),
        ],
        interpretation="comparing Aspirin vs Clopidogrel by phase",
    )


def _cohort_rows():
    return [
        {"phase": "Phase 2", "series": "Aspirin", "trial_count": 80, "total_contributors": 80, "references": []},
        {"phase": "Phase 2", "series": "Clopidogrel", "trial_count": 20, "total_contributors": 20, "references": []},
    ]


def test_cohort_grouped_bar_encoding():
    resp = build_response(_cohort_plan(), [], total=100, filters_applied={}, exact_rows=_cohort_rows())
    enc = resp.visualization.encoding
    assert resp.visualization.type == VizType.grouped_bar
    assert enc.x.field == "phase"
    assert enc.color.field == "series"  # one series per cohort
    assert enc.y.field == "trial_count"
    assert "Aspirin" in resp.visualization.title and "Clopidogrel" in resp.visualization.title


def test_cohort_meta_marks_comparison_and_full_population():
    resp = build_response(_cohort_plan(), [], total=100, filters_applied={}, exact_rows=_cohort_rows())
    assert resp.meta.grouping == "cohort comparison"
    assert resp.meta.trials_aggregated == 100  # exact path: full population
    assert resp.meta.warnings == []  # no sampling warning


def test_cohort_aggregated_override_flags_sampling():
    # non-facetable fallback supplies sampled rows + an explicit aggregated count
    resp = build_response(
        _cohort_plan(), [], total=100, filters_applied={}, exact_rows=_cohort_rows(), aggregated_override=40
    )
    assert resp.meta.trials_aggregated == 40
    assert resp.meta.warnings  # sampling honestly surfaced
