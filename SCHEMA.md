# Cherion Response Schema

This document is the contract for frontend renderers. Given a `POST /visualize`
response, a renderer can draw the chart **without guessing** by reading
`visualization.type` and `visualization.encoding`.

## Request

```jsonc
POST /visualize
{
  "query": "Trials by phase for pembrolizumab",   // REQUIRED — natural language
  // Optional explicit overrides (take precedence over the LLM's interpretation):
  "drug_name": "pembrolizumab",
  "condition": "lung cancer",
  "sponsor": "Merck",
  "country": "United States",
  "trial_phase": ["PHASE2", "PHASE3"],            // CT.gov enums
  "status": ["RECRUITING"],                        // CT.gov enums
  "start_year": 2015,
  "end_year": 2024,
  "max_records": 300                               // cap records pulled for aggregation
}
```

## Response envelope

```jsonc
{
  "visualization": {
    "type": "bar_chart",          // see Visualization types below
    "title": "Trials by Phase",
    "encoding": { ... },          // channel -> field mapping; shape depends on type
    "data": [ ... ] | { ... }     // array for charts/geo; object for network
  },
  "meta": { ... }
}
```

### `encoding` channels

Each channel is `{ "field": str, "type": "nominal|ordinal|quantitative|temporal", "title": str }`.
Only channels relevant to the viz type are present.

| Channel | Used by |
|---|---|
| `x`, `y` | bar, grouped_bar, time_series, histogram, scatter |
| `color` | grouped_bar (series), geo_map (choropleth value) |
| `size` | optional point sizing |
| `region` | geo_map (choropleth key) |
| `lat`, `lng` | geo_map (point map) |
| `nodes`, `edges` | network_graph (descriptors; data is in `data.nodes`/`data.edges`) |

### `meta`

```jsonc
{
  "source": "clinicaltrials.gov",
  "filters": { "drug_name": "pembrolizumab" },   // filters actually applied
  "query_interpretation": "Count trials grouped by phase, filtered to intervention=pembrolizumab",
  "total_matching_trials": 2890,   // total matches at CT.gov
  "trials_aggregated": 300,        // how many we actually aggregated
  "units": "trials",               // or "participants" for enrollment metrics
  "sorting": "value desc",
  "time_granularity": "year",      // time_series only
  "grouping": "status",            // secondary dimension, if any
  "notes": ["..."],                // assumptions / interpretation
  "warnings": ["Aggregated over 300 of 2890 ..."]  // sampling/empty-result flags
}
```

> **Exact vs. sampled counts:**
> - **Exact** — count-based `bar_chart`/`grouped_bar` over enum dimensions
>   (`phase`, `status`, `study_type`, `sponsor_class`) are computed with faceted
>   `countTotal` queries over the **full** population. Here
>   `trials_aggregated == total_matching_trials`, `warnings` is empty, and `notes`
>   says "Exact counts via faceted queries…".
> - **Sampled** — high-cardinality dimensions (`sponsor`, `condition`, `country`,
>   `intervention`), `time_series`, `histogram`, `scatter_plot`, `network_graph`,
>   `geo_map` aggregate a large record sample. When
>   `trials_aggregated < total_matching_trials`, counts reflect the sample and a
>   `warnings` entry says so. **Render that warning prominently.**

## Deep citations (every datum)

Every data point (bar, bucket, point, node, edge) carries provenance:

```jsonc
{
  "...": "...",
  "total_contributors": 78,        // total trials behind this datum
  "references": [                  // capped to 5 exact citations
    { "nct_id": "NCT05996523",
      "field": "protocolSection.designModule.phases",
      "value": "PHASE2" }          // exact value from the API response
  ]
}
```

Link any `nct_id` to `https://clinicaltrials.gov/study/<nct_id>`.

## Visualization types

### `bar_chart`
`encoding`: `x` (category), `y` (metric). `data`: rows.
```jsonc
{ "phase": "Phase 2", "trial_count": 120, "total_contributors": 120, "references": [...] }
```
The category field name equals `encoding.x.field` (e.g. `phase`, `sponsor`, `status`,
`country`, `condition`, `study_type`, `intervention`, `intervention_type`).
The value field equals `encoding.y.field` (`trial_count`, `enrollment_sum`, or `enrollment_avg`).

### `grouped_bar`
`encoding`: `x` (primary category), `y` (`trial_count`), `color` (secondary category).
```jsonc
{ "phase": "Phase 2", "status": "Recruiting", "trial_count": 40, "references": [...] }
```

**Comparison variant ("A vs B" questions).** When the query compares named cohorts
(e.g. "Aspirin vs Clopidogrel"), the result is a `grouped_bar` whose series are the
cohorts: `color.field` is the literal `"series"` and `meta.grouping` is
`"cohort comparison"`. Rows are keyed by `encoding.x.field` + `series` — the frontend
reads `encoding.color.field` dynamically, so no special-casing is needed.
```jsonc
{ "phase": "Phase 2", "series": "Aspirin", "trial_count": 80, "references": [...] }
```

### `time_series`
`encoding`: `x` = `period` (temporal), `y` = `trial_count`. `data` sorted ascending by period.
```jsonc
{ "period": "2019", "trial_count": 33, "references": [...] }   // or "2019-06" if granularity=month
```

### `histogram`
`encoding`: `x` = `bin_label` (ordinal), `y` = `trial_count`. Bins over enrollment size.
```jsonc
{ "bin_start": 0, "bin_end": 100, "bin_label": "0–100", "trial_count": 52, "references": [...] }
```

### `scatter_plot`
`encoding`: `x` = `enrollment`, `y` = `duration_days`. One point per trial.
```jsonc
{ "nct_id": "NCT...", "enrollment": 851, "duration_days": 2438, "references": [...] }
```

### `network_graph`
`data` is an **object**: `{ "nodes": [...], "edges": [...] }`.
```jsonc
"nodes": [ { "id": "drug:Pembrolizumab", "label": "Pembrolizumab",
             "group": "drug", "weight": 120, "references": [...] } ],
"edges": [ { "source": "drug:Pembrolizumab", "target": "condition:NSCLC",
             "weight": 34, "references": [...] } ]
```
`group` ∈ {`drug`,`condition`,`sponsor`,`site`}. `weight` = number of trials.
Edge `weight` = trials where both endpoints co-occur.

### `geo_map`
`data` is an **object**: `{ "regions": [...], "points": [...] }`.
```jsonc
"regions": [ { "region": "United States", "trial_count": 180, "references": [...] } ],  // choropleth
"points":  [ { "lat": 42.36, "lng": -71.06, "label": "Boston",
               "trial_count": 12, "references": [...] } ]                                // point map
```
A trial counts once per region (a trial may span multiple regions — see `notes`).
```
