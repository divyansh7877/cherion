import EChart from "../EChart";
import { axisStyle, baseOption, palette } from "../../theme";
import type { CitationSelection, Datum, Visualization } from "../../types";

interface Props {
  viz: Visualization;
  onSelect: (sel: CitationSelection) => void;
}

/** Single-dimension bar chart. x = category field, y = metric field. */
export default function Bar({ viz, onSelect }: Props) {
  const rows = viz.data as Datum[];
  const xf = viz.encoding.x!.field;
  const yf = viz.encoding.y!.field;

  const option = {
    ...baseOption,
    tooltip: { ...baseOption.tooltip, trigger: "axis" as const, axisPointer: { type: "shadow" as const } },
    xAxis: {
      type: "category" as const,
      data: rows.map((r) => String(r[xf])),
      name: viz.encoding.x!.title ?? xf,
      nameLocation: "middle" as const,
      nameGap: 40,
      axisLabel: { ...axisStyle.axisLabel, interval: 0, rotate: rows.length > 6 ? 30 : 0 },
      axisLine: axisStyle.axisLine,
    },
    yAxis: {
      type: "value" as const,
      name: viz.encoding.y!.title ?? yf,
      ...axisStyle,
    },
    series: [
      {
        type: "bar" as const,
        data: rows.map((r, i) => ({
          value: Number(r[yf]),
          itemStyle: { color: palette[i % palette.length], borderRadius: [3, 3, 0, 0] },
        })),
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
          label: `${row[xf]} — ${row[yf]} ${viz.encoding.y!.title ?? ""}`.trim(),
          totalContributors: row.total_contributors,
          references: row.references,
        });
      }}
    />
  );
}
