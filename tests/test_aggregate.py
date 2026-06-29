from app.agg import aggregate as agg
from app.agg import extractors as ex
from app.schemas import Dimension, Metric


def test_categorical_counts_sum_to_unique_study_group_pairs(pembro_studies):
    rows, _ = agg.aggregate_categorical(pembro_studies, Dimension.phase)
    # every study contributes exactly one phase group (phases defaults to NA),
    # and a study counts once per distinct phase label.
    total = sum(r["trial_count"] for r in rows)
    expected = len(
        {(ex.nct_id(s), lbl) for s in pembro_studies for lbl, _, _ in ex.extract_dimension(s, Dimension.phase)}
    )
    assert total == expected


def test_categorical_rows_have_citations(pembro_studies):
    rows, _ = agg.aggregate_categorical(pembro_studies, Dimension.phase)
    for r in rows:
        assert r["references"], "every datum must cite contributing trials"
        ref = r["references"][0]
        assert ref["nct_id"].startswith("NCT")
        assert ref["field"] == "protocolSection.designModule.phases"
        assert r["total_contributors"] >= len(r["references"])


def test_categorical_sorted_desc(pembro_studies):
    rows, _ = agg.aggregate_categorical(pembro_studies, Dimension.status)
    counts = [r["trial_count"] for r in rows]
    assert counts == sorted(counts, reverse=True)


def test_limit_truncates_and_notes(diabetes_studies):
    rows, notes = agg.aggregate_categorical(diabetes_studies, Dimension.sponsor, limit=5)
    assert len(rows) <= 5
    assert any("top 5" in n for n in notes)


def test_dedup_same_study_same_phase_counts_once():
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT1"},
            "designModule": {"phases": ["PHASE2", "PHASE2"]},
        }
    }
    rows, _ = agg.aggregate_categorical([study], Dimension.phase)
    assert len(rows) == 1
    assert rows[0]["trial_count"] == 1


def test_time_series_sorted_and_cited(diabetes_studies):
    rows, _ = agg.aggregate_time_series(diabetes_studies, "year")
    periods = [r["period"] for r in rows]
    assert periods == sorted(periods)
    assert all(r["references"] for r in rows)


def test_histogram_bins_and_counts(pembro_studies):
    rows, notes = agg.aggregate_histogram(pembro_studies)
    n_with_enroll = sum(1 for s in pembro_studies if ex.enrollment_count(s) is not None)
    assert sum(r["trial_count"] for r in rows) == n_with_enroll
    assert all("bin_label" in r for r in rows)


def test_scatter_points_have_two_numerics(pembro_studies):
    rows, _ = agg.aggregate_scatter(pembro_studies)
    for r in rows:
        assert isinstance(r["enrollment"], int)
        assert isinstance(r["duration_days"], int)


def test_enrollment_sum_metric(pembro_studies):
    rows, _ = agg.aggregate_categorical(
        pembro_studies, Dimension.phase, Metric.enrollment_sum, value_field="enrollment_sum"
    )
    assert all("enrollment_sum" in r for r in rows)
    assert sum(r["enrollment_sum"] for r in rows) > 0
