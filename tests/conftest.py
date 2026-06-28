import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _offline_planner(monkeypatch):
    """Force the deterministic heuristic planner during tests so they never make
    real Anthropic calls (a valid key in .env must not turn tests into network tests)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(scope="session")
def pembro() -> dict:
    return _load("pembrolizumab.json")


@pytest.fixture(scope="session")
def diabetes() -> dict:
    return _load("diabetes.json")


@pytest.fixture(scope="session")
def pembro_studies(pembro) -> list[dict]:
    return pembro["studies"]


@pytest.fixture(scope="session")
def diabetes_studies(diabetes) -> list[dict]:
    return diabetes["studies"]
