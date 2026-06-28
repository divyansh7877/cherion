from app.agg import extractors as ex
from app.schemas import Dimension


def test_nct_id(pembro_studies):
    assert ex.nct_id(pembro_studies[0]).startswith("NCT")


def test_phase_extractor_returns_label_and_citation(pembro_studies):
    triples = ex.extract_dimension(pembro_studies[0], Dimension.phase)
    assert triples
    label, field, raw = triples[0]
    assert field == "protocolSection.designModule.phases"
    assert raw in {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"}
    assert label  # human label present


def test_sponsor_extractor(pembro_studies):
    triples = ex.extract_dimension(pembro_studies[0], Dimension.sponsor)
    assert len(triples) == 1
    assert triples[0][1] == "protocolSection.sponsorCollaboratorsModule.leadSponsor.name"


def test_condition_can_be_multivalued(pembro_studies):
    # at least one study has multiple conditions across the fixture
    multi = [s for s in pembro_studies if len(ex.extract_dimension(s, Dimension.condition)) > 1]
    assert multi


def test_enrollment_count_is_int_or_none(pembro_studies):
    vals = [ex.enrollment_count(s) for s in pembro_studies]
    assert all(v is None or isinstance(v, int) for v in vals)
    assert any(isinstance(v, int) for v in vals)


def test_start_year_parses(pembro_studies):
    years = [ex.extract_dimension(s, Dimension.start_year) for s in pembro_studies]
    flat = [t for ts in years for t in ts]
    assert flat
    assert all(t[0].isdigit() and len(t[0]) == 4 for t in flat)
