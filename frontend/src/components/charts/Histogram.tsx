import EChart from "../EChart";
import { axisStyle, baseOption, tokens } from "../../theme";
import type { CitationSelection, Datum, Visualization } from "../../types";

interface Props {
  viz: Visualization;
  onSelect: (sel: CitationSelection) => void;
}

/** Enrollment histogram. Bars ordered by bin_start, no gap (continuous look). */
export default function Histogram({ viz, onSelect }: Props) {
  const rows = ([...(viz.data as Datum[])]).sort(
    (a, b) => Number(a.bin_start) - Number(b.bin_start),
  );
  const yf = viz.encoding.y!.field;

  const option = {
    ...baseOption,
    tooltip: { ...baseOption.tooltip, trigger: "axis" as const, axisPointer: { type: "shadow" as const } },
    xAxis: {
      type: "category" as const,
      data: rows.map((r) => String(r.bin_label)),
      name: viz.encoding.x!.title ?? "Enrollment Range",
      nameLocation: "middle" as const,
      nameGap: 40,
      axisLabel: { ...axisStyle.axisLabel, interval: 0, rotate: rows.length > 8 ? 30 : 0 },
      axisLine: axisStyle.axisLine,
    },
    yAxis: { type: "value" as const, name: viz.encoding.y!.title ?? yf, ...axisStyle },
    series: [
      {
        type: "bar" as const,
        data: rows.map((r) => Number(r[yf])),
        barCategoryGap: "2%",
        itemStyle: { color: tokens.accent },
        emphasis: { itemStyle: { color: "#6aa9fa" } },
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
          label: `Enrollment ${row.bin_label} — ${row[yf]} trials`,
          totalContributors: row.total_contributors,
          references: row.references,
        });
      }}
    />
  );
}
