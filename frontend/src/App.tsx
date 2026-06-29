import { useCallback, useEffect, useState } from "react";
import { postVisualize } from "./api";
import QueryBar from "./components/QueryBar";
import FilterControls from "./components/FilterControls";
import ResultCard from "./components/ResultCard";
import VizRenderer from "./components/VizRenderer";
import CitationPanel from "./components/CitationPanel";
import RawSchema from "./components/RawSchema";
import { EMPTY_FILTERS } from "./types";
import type { CitationSelection, OverrideFilters, VisualizeRequest, VisualizeResponse } from "./types";

const DEFAULT_QUERY = "Trials by phase for pembrolizumab";

function buildRequest(query: string, f: OverrideFilters): VisualizeRequest {
  const req: VisualizeRequest = { query, max_records: 3000 };
  if (f.drug_name) req.drug_name = f.drug_name;
  if (f.condition) req.condition = f.condition;
  if (f.sponsor) req.sponsor = f.sponsor;
  if (f.country) req.country = f.country;
  if (f.trial_phase.length) req.trial_phase = f.trial_phase;
  if (f.status.length) req.status = f.status;
  if (f.start_year) req.start_year = Number(f.start_year);
  if (f.end_year) req.end_year = Number(f.end_year);
  return req;
}

export default function App() {
  const [query, setQuery] = useState(DEFAULT_QUERY);
  const [filters, setFilters] = useState<OverrideFilters>(EMPTY_FILTERS);
  const [response, setResponse] = useState<VisualizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selection, setSelection] = useState<CitationSelection | null>(null);

  const runQuery = useCallback(async (q: string, f: OverrideFilters) => {
    if (!q) return;
    setQuery(q);
    setLoading(true);
    setError(null);
    setSelection(null);
    const url = new URL(window.location.href);
    url.searchParams.set("q", q);
    window.history.replaceState({}, "", url);
    try {
      setResponse(await postVisualize(buildRequest(q, f)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load: honor ?q= deep link, else the default example.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q") || DEFAULT_QUERY;
    runQuery(q, EMPTY_FILTERS);
  }, [runQuery]);

  return (
    <div className="app">
      <header>
        <div>
          <div className="brand">Cherion</div>
          <div className="header-sub">
            Natural-language clinical-trial questions, answered as cited visualizations.
          </div>
        </div>
        <div className="header-tag">ClinicalTrials.gov · v0.1</div>
      </header>

      <main>
        <QueryBar initialQuery={query} loading={loading} onSubmit={(q) => runQuery(q, filters)} />
        <FilterControls value={filters} onChange={setFilters} onApply={() => runQuery(query, filters)} />

        {error && <div className="banner error-banner">Error: {error}</div>}

        {loading && !response && <div className="card skeleton">Querying ClinicalTrials.gov…</div>}

        {response && (
          <div className="card">
            <ResultCard title={response.visualization.title} meta={response.meta} />
            <div className="viz-layout">
              <div className="viz-main">
                <VizRenderer viz={response.visualization} onSelect={setSelection} />
              </div>
              <CitationPanel selection={selection} />
            </div>
            <RawSchema response={response} />
          </div>
        )}
      </main>

      <footer>
        Cherion · LLM plans the query, deterministic code computes every number, every datum is cited.
      </footer>
    </div>
  );
}
