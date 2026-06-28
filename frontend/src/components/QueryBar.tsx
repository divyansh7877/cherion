import { useState } from "react";

interface Props {
  initialQuery: string;
  loading: boolean;
  onSubmit: (query: string) => void;
}

const EXAMPLES = [
  "Trials by phase for pembrolizumab",
  "Compare trials by phase and status for breast cancer",
  "Number of diabetes trials started each year since 2015",
  "Distribution of enrollment size for recruiting lung cancer trials",
  "Network of drugs and conditions for CAR-T trials",
  "Where are recruiting Alzheimer's trials located by country",
];

export default function QueryBar({ initialQuery, loading, onSubmit }: Props) {
  const [value, setValue] = useState(initialQuery);

  return (
    <div className="querybar">
      <div className="querybar-row">
        <input
          type="text"
          value={value}
          placeholder="Ask a clinical-trials question…"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSubmit(value.trim())}
        />
        <button disabled={loading || !value.trim()} onClick={() => onSubmit(value.trim())}>
          {loading ? "Loading…" : "Visualize"}
        </button>
      </div>
      <div className="examples">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            className="chip"
            onClick={() => {
              setValue(ex);
              onSubmit(ex);
            }}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
