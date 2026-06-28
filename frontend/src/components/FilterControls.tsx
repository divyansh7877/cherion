import { useState } from "react";
import { PHASES, STATUSES } from "../types";
import type { OverrideFilters } from "../types";

interface Props {
  value: OverrideFilters;
  onChange: (next: OverrideFilters) => void;
  onApply: () => void;
}

const PHASE_LABELS: Record<string, string> = {
  EARLY_PHASE1: "Early 1",
  PHASE1: "Phase 1",
  PHASE2: "Phase 2",
  PHASE3: "Phase 3",
  PHASE4: "Phase 4",
  NA: "N/A",
};

export default function FilterControls({ value, onChange, onApply }: Props) {
  const [open, setOpen] = useState(false);
  const set = (patch: Partial<OverrideFilters>) => onChange({ ...value, ...patch });
  const toggle = (key: "trial_phase" | "status", v: string) => {
    const arr = value[key];
    set({ [key]: arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v] } as Partial<OverrideFilters>);
  };

  const activeCount =
    [value.drug_name, value.condition, value.sponsor, value.country, value.start_year, value.end_year].filter(
      Boolean,
    ).length +
    value.trial_phase.length +
    value.status.length;

  return (
    <div className="filters">
      <button className="filters-toggle" onClick={() => setOpen(!open)}>
        {open ? "▾" : "▸"} Advanced filters{activeCount ? ` (${activeCount})` : ""}
      </button>
      {open && (
        <div className="filters-body">
          <div className="filters-grid">
            <label>
              Drug / intervention
              <input value={value.drug_name} onChange={(e) => set({ drug_name: e.target.value })} />
            </label>
            <label>
              Condition
              <input value={value.condition} onChange={(e) => set({ condition: e.target.value })} />
            </label>
            <label>
              Sponsor
              <input value={value.sponsor} onChange={(e) => set({ sponsor: e.target.value })} />
            </label>
            <label>
              Country
              <input value={value.country} onChange={(e) => set({ country: e.target.value })} />
            </label>
            <label>
              Start year ≥
              <input
                type="number"
                value={value.start_year}
                onChange={(e) => set({ start_year: e.target.value })}
              />
            </label>
            <label>
              End year ≤
              <input
                type="number"
                value={value.end_year}
                onChange={(e) => set({ end_year: e.target.value })}
              />
            </label>
          </div>

          <div className="filters-chips">
            <span className="filters-label">Phase</span>
            {PHASES.map((p) => (
              <button
                key={p}
                className={`chip ${value.trial_phase.includes(p) ? "chip-on" : ""}`}
                onClick={() => toggle("trial_phase", p)}
              >
                {PHASE_LABELS[p] ?? p}
              </button>
            ))}
          </div>
          <div className="filters-chips">
            <span className="filters-label">Status</span>
            {STATUSES.map((s) => (
              <button
                key={s}
                className={`chip ${value.status.includes(s) ? "chip-on" : ""}`}
                onClick={() => toggle("status", s)}
              >
                {s.replace(/_/g, " ").toLowerCase()}
              </button>
            ))}
          </div>

          <div className="filters-actions">
            <button className="apply" onClick={onApply}>
              Apply filters
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
