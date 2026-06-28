import EChart from "../EChart";
import { axisStyle, baseOption, tokens } from "../../theme";
import type { CitationSelection, Datum, Visualization } from "../../types";

interface Props {
  viz: Visualization;
  onSelect: (sel: CitationSelection) => void;
}

/** Scatter: one point per trial. x = enrollment, y = duration_days. */
export default function Scatter({ viz, onSelect }: Props) {
  const rows = viz.data as Datum[];
  const xf = viz.encoding.x!.field;
  const yf = viz.encoding.y!.field;

  const option = {
    ...baseOption,
    tooltip: {
      ...baseOption.tooltip,
      trigger: "item" as const,
      formatter: (p: { dataIndex: number }) => {
        const r = rows[p.dataIndex];
        return `${r.nct_id}<br/>${viz.encoding.x!.title}: ${r[xf]}<br/>${viz.encoding.y!.title}: ${r[yf]}`;
      },
    },
    xAxis: { type: "value" as const, name: viz.encoding.x!.title ?? xf, nameLocation: "middle" as const, nameGap: 32, ...axisStyle },
    yAxis: { type: "value" as const, name: viz.encoding.y!.title ?? yf, ...axisStyle },
    series: [
      {
        type: "scatter" as const,
        symbolSize: 9,
        data: rows.map((r) => [Number(r[xf]), Number(r[yf])]),
        itemStyle: { color: "rgba(68,147,248,0.6)", borderColor: tokens.accent },
      },
    ],
  };

  return (
    <EChart
      option={option}
      onDatumClick={(info) => {
        const row = rows[info.dataIndex];
        if (!row) return;
        onSelect({
          label: `${row.nct_id} — ${viz.encoding.x!.title}: ${row[xf]}, ${viz.encoding.y!.title}: ${row[yf]}`,
          totalContributors: row.total_contributors,
          references: row.references,
        });
      }}
    />
  );
}
