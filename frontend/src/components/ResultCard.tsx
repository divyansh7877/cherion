import type { Meta } from "../types";

export default function ResultCard({ title, meta }: { title: string; meta: Meta }) {
  return (
    <div className="result-head">
      <h2>{title}</h2>
      {meta.query_interpretation && (
        <p className="interp">Interpreted as: {meta.query_interpretation}</p>
      )}
      <div className="meta-line">
        {meta.trials_aggregated != null && meta.total_matching_trials != null && (
          <span>
            {meta.trials_aggregated === meta.total_matching_trials
              ? `Exact over all ${meta.total_matching_trials.toLocaleString()} trials`
              : `Aggregated ${meta.trials_aggregated.toLocaleString()} of ${meta.total_matching_trials.toLocaleString()} trials`}
          </span>
        )}
        {meta.units && <span>· units: {meta.units}</span>}
        <span>· source: {meta.source}</span>
      </div>
      {meta.warnings.map((w, i) => (
        <div key={i} className="banner warn-banner">
          ⚠ {w}
        </div>
      ))}
      {meta.notes.length > 0 && (
        <details className="notes">
          <summary>{meta.notes.length} note(s) about this result</summary>
          <ul>
            {meta.notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
