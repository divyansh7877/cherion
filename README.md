# Cherion

**Natural-language clinical-trial questions → structured, cited visualization specs.**

Cherion turns a question like *"Trials by phase for pembrolizumab"* into a
renderer-ready visualization specification, backed by real
[ClinicalTrials.gov](https://clinicaltrials.gov/data-api/api) data with deep
citations for every data point.

## Core idea: LLM at the edges, math in the middle

The single design principle that prevents hallucinated numbers:

```
NL query ─▶ Planner (LLM, forced tool-use) ─▶ QueryPlan ─▶ Executor (pure Python)
                                                              │ fetch + aggregate
                              VisualizationSpec + citations ◀─┘
```

- **The LLM only plans.** It converts the query into a structured `QueryPlan`
  (filters, group-by dimension, metric, viz type) via Anthropic **forced
  tool-use** — it never emits data points or counts.
- **Deterministic code computes every number** from real API records and attaches
  **deep citations** (`nct_id` + exact field value) to every datum.

This means counts are reproducible and verifiable, and citations can never drift
from the data because they are produced by the same aggregation pass.

## Supported visualizations

`bar_chart` · `grouped_bar` · `time_series` · `histogram` · `scatter_plot` ·
`network_graph` (entity co-occurrence) · `geo_map` (choropleth + point map)

All query classes flow through **one pipeline**; new dimensions/viz types are
registry additions, not new code paths. See the plan/design notes for details.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                # then edit .env and paste your key
```

`.env` (gitignored) is loaded automatically at startup:

```ini
ANTHROPIC_API_KEY=sk-ant-...        # optional — falls back to a heuristic planner if absent
CHERION_MODEL=claude-sonnet-4-6     # optional
```

Real environment variables still override `.env`, so `export ANTHROPIC_API_KEY=...`
also works.

## Run

### Backend
```bash
uvicorn app.main:app --reload --port 8077
# API at http://localhost:8077  (POST /visualize, GET /health)
```

### Frontend (React + TypeScript + Vite)

The demo is a typed React SPA using **Apache ECharts** (charts + network graph) and
**Leaflet** (geographic map), with click-to-cite drill-down on every datum and a
**Download JSON / Copy** action to export the raw response schema.

```bash
cd frontend
npm install
npm run dev        # dev server on http://localhost:5173 (proxies /visualize to :8077)
```

For a production-style demo, build once and let FastAPI serve it:
```bash
cd frontend && npm run build      # emits frontend/dist
uvicorn app.main:app --port 8077  # open http://localhost:8077
```

### Example request

```bash
curl -s localhost:8077/visualize -H 'Content-Type: application/json' \
  -d '{"query":"Trials by phase for pembrolizumab","max_records":1000}' | jq
```

### Example queries (one per viz type)

| Query | Viz |
|---|---|
| Trials by phase for pembrolizumab | bar_chart |
| Compare trials by phase and status for breast cancer | grouped_bar |
| Compare phases for trials involving Aspirin vs Clopidogrel | grouped_bar (cohort comparison) |
| Number of diabetes trials started each year since 2015 | time_series |
| Distribution of enrollment size for recruiting lung cancer trials | histogram |
| Enrollment vs duration for melanoma trials | scatter_plot |
| Network of drugs and conditions for CAR-T trials | network_graph |
| Where are recruiting Alzheimer's trials located by country | geo_map |

## API

- `POST /visualize` — `{ "query": "...", ...optional overrides }` → visualization spec.
- `GET /health` — liveness.
- `GET /` — the demo page.

The full response contract is in **[SCHEMA.md](SCHEMA.md)** — a frontend engineer
can implement a renderer from that document alone.

## Anti-hallucination guarantees

| Risk | Mitigation |
|---|---|
| Invented numbers | All metrics computed in pure Python from records (unit-tested). |
| Bad filters/enums | Deterministic plan→params mapping + repair layer clamps illegal combos. |
| Plan schema drift | Anthropic forced tool-use → Pydantic-validated `QueryPlan`. |
| Unsupported provenance | Every datum cites real `nct_id`s + exact field values. |
| Silent truncation | `meta.total_matching_trials` vs `trials_aggregated` + a `warnings` entry. |

### Exact vs. sampled counts

Count-based **bar / grouped-bar** charts over bounded-enum dimensions (`phase`,
`status`, `study_type`, `sponsor_class`) are **exact over the full population** —
computed with concurrent faceted `countTotal` queries (one per category), not by
sampling records. `meta.trials_aggregated == total_matching_trials` and there's no
sampling warning. Example: *trials by phase for breast cancer* counts all 16,541
trials in ~3s, with example trials cited per bar.

Other viz types (high-cardinality dimensions, time series, histogram, scatter,
network, geo) aggregate a large sample (up to 1,000 records) and **flag it
honestly** in `meta.warnings`.

## Tests

```bash
pytest -q          # 63 tests over real captured fixtures + mocked API
ruff check app/
```

Tests run against captured ClinicalTrials.gov responses in `tests/fixtures/`, so
aggregation correctness is checked against real data without network calls.

## Development notes

### Tools used

- **Backend:** Python 3.11, FastAPI, Pydantic v2 (schema validation), `httpx`
  (async API client), Anthropic Python SDK (forced tool-use for planning).
- **Frontend:** React 18 + TypeScript + Vite, Apache ECharts (charts + force-layout
  network graph), Leaflet (geographic map).
- **Data source:** the public ClinicalTrials.gov v2 REST API — no scraping, no
  intermediate datastore.
- **Quality:** `pytest` (unit + end-to-end), `ruff` (lint + format).
- **AI assistance:** Claude (via Claude Code) was used as a pair-programmer for
  scaffolding, refactoring, and tests; all architecture decisions, the data model,
  and the correctness strategy were author-directed and reviewed line by line.

### How correctness was validated

- **No invented numbers by construction.** The LLM only emits a validated
  `QueryPlan`; every count, sum, and bin is computed in pure Python, so results are
  reproducible and unit-testable.
- **Tests against real data.** Aggregation is verified against captured
  ClinicalTrials.gov responses in `tests/fixtures/`, plus mocked-API tests for the
  faceted-count and cohort-comparison paths — 63 tests, no network required.
- **Exact counts cross-checked against the API.** Faceted `countTotal` queries were
  validated against the totals ClinicalTrials.gov reports for the same filters (e.g.
  *breast cancer by phase* → all 16,541 trials), confirming the charts reflect the
  full population rather than a sample.
- **Honest provenance.** `meta.total_matching_trials` vs `trials_aggregated` and a
  `warnings` field make any sampling explicit, and every datum carries clickable
  `nct_id` citations that link back to the source record for manual verification.

### Designed deliberately vs. generated and adapted

- **Deliberately designed** — the parts that define the project:
  - the *"LLM at the edges, math in the middle"* architecture and the `QueryPlan`
    intermediate representation;
  - the single-pipeline routing that covers all viz types without per-query hacks;
  - the faceted exact-count strategy and the cohort-comparison model;
  - the deep-citation contract (`nct_id` + field + value) carried end to end;
  - the response schema ([SCHEMA.md](SCHEMA.md)) as the frontend's typed contract.
- **Generated then adapted** — assistant-drafted, then reviewed, tightened, and
  integrated: API-client boilerplate, React component scaffolding and CSS, test
  fixtures, and documentation prose. Nothing was accepted unread.

## Layout

```
app/
  schemas.py           # request, QueryPlan IR, response models
  planner.py           # LLM forced tool-use -> QueryPlan + repair layer
  clinicaltrials/      # async API client + plan->params mapping
  agg/                 # extractors, aggregate, network, geo, citations (pure)
  spec_builder.py      # plan + rows -> encoding + data
  pipeline.py          # request -> plan -> fetch -> aggregate -> spec
  main.py              # FastAPI app
frontend/              # React + TS + Vite SPA (ECharts + Leaflet); types.ts mirrors SCHEMA.md
tests/                 # fixtures + unit/e2e tests
SCHEMA.md              # frontend rendering contract
```
