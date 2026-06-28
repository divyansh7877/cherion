import EChart from "../EChart";
import { axisStyle, baseOption, tokens } from "../../theme";
import type { CitationSelection, Datum, Visualization } from "../../types";

interface Props {
  viz: Visualization;
  onSelect: (sel: CitationSelection) => void;
}

/** Time series line. x = period, y = trial_count. */
export default function TimeSeries({ viz, onSelect }: Props) {
  const rows = viz.data as Datum[];
  const xf = viz.encoding.x!.field; // "period"
  const yf = viz.encoding.y!.field; // "trial_count"

  const option = {
    ...baseOption,
    tooltip: { ...baseOption.tooltip, trigger: "axis" as const },
    dataZoom: rows.length > 20 ? [{ type: "inside" }, { type: "slider", bottom: 8 }] : undefined,
    xAxis: {
      type: "category" as const,
      data: rows.map((r) => String(r[xf])),
      name: viz.encoding.x!.title ?? xf,
      nameLocation: "middle" as const,
      nameGap: 36,
      boundaryGap: false,
      ...axisStyle,
    },
    yAxis: { type: "value" as const, name: viz.encoding.y!.title ?? yf, ...axisStyle },
    series: [
      {
        type: "line" as const,
        smooth: true,
        showSymbol: true,
        symbolSize: 7,
        data: rows.map((r) => Number(r[yf])),
        lineStyle: { color: tokens.accent, width: 2 },
        itemStyle: { color: tokens.accent },
        areaStyle: { color: "rgba(68,147,248,0.15)" },
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
          label: `${row[xf]} — ${row[yf]} trials`,
          totalContributors: row.total_contributors,
          references: row.references,
        });
      }}
    />
  );
}
