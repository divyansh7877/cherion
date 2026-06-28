import { STUDY_URL } from "../types";
import type { CitationSelection } from "../types";

interface Props {
  selection: CitationSelection | null;
}

/** Deep-citation drill-down for the datum the user clicked. */
export default function CitationPanel({ selection }: Props) {
  if (!selection) {
    return (
      <aside className="citations citations-empty">
        <div className="citations-title">Citations</div>
        <p className="muted">
          Click any bar, point, node, or row to trace it back to the underlying
          ClinicalTrials.gov records.
        </p>
      </aside>
    );
  }

  return (
    <aside className="citations">
      <div className="citations-title">Citations</div>
      <div className="citations-subject">{selection.label}</div>
      <div className="muted citations-count">
        Backed by {selection.totalContributors} trial
        {selection.totalContributors === 1 ? "" : "s"}
        {selection.references.length < selection.totalContributors
          ? ` · showing ${selection.references.length}`
          : ""}
      </div>
      <ul className="citation-list">
        {selection.references.map((ref, i) => (
          <li key={i}>
            <a href={STUDY_URL(ref.nct_id)} target="_blank" rel="noreferrer">
              {ref.nct_id}
            </a>
            <div className="citation-field">{ref.field}</div>
            <div className="citation-value">“{ref.value}”</div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
