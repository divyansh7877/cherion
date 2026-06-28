import EChart from "../EChart";
import { axisStyle, baseOption, palette } from "../../theme";
import type { CitationSelection, Datum, Visualization } from "../../types";

interface Props {
  viz: Visualization;
  onSelect: (sel: CitationSelection) => void;
}

/** Grouped bar: primary category on x, one series per secondary (color) value. */
export default function GroupedBar({ viz, onSelect }: Props) {
  const rows = viz.data as Datum[];
  const xf = viz.encoding.x!.field;
  const yf = viz.encoding.y!.field;
  const cf = viz.encoding.color!.field;

  const categories = [...new Set(rows.map((r) => String(r[xf])))];
  const seriesNames = [...new Set(rows.map((r) => String(r[cf])))];

  // index for click lookups: "category||series" -> row
  const byKey = new Map<string, Datum>();
  rows.forEach((r) => byKey.set(`${r[xf]}||${r[cf]}`, r));

  const series = seriesNames.map((sName, i) => ({
    name: sName,
    type: "bar" as const,
    data: categories.map((c) => {
      const row = byKey.get(`${c}||${sName}`);
      return row ? Number(row[yf]) : 0;
    }),
    itemStyle: { color: palette[i % palette.length] },
  }));

  const option = {
    ...baseOption,
    tooltip: { ...baseOption.tooltip, trigger: "axis" as const, axisPointer: { type: "shadow" as const } },
    legend: { top: 0, textStyle: { color: "#8b98a5" }, data: seriesNames },
    grid: { ...baseOption.grid, top: 40 },
    xAxis: {
      type: "category" as const,
      data: categories,
      name: viz.encoding.x!.title ?? xf,
      nameLocation: "middle" as const,
      nameGap: 40,
      axisLabel: { ...axisStyle.axisLabel, interval: 0, rotate: categories.length > 6 ? 30 : 0 },
      axisLine: axisStyle.axisLine,
    },
    yAxis: { type: "value" as const, name: viz.encoding.y!.title ?? yf, ...axisStyle },
    series,
  };

  return (
    <EChart
      option={option}
      onDatumClick={(info) => {
        const category = categories[info.dataIndex];
        const sName = seriesNames[info.seriesIndex];
        const row = byKey.get(`${category}||${sName}`);
        if (!row) return;
        onSelect({
          label: `${category} · ${sName} — ${row[yf]} trials`,
          totalContributors: row.total_contributors,
          references: row.references,
        });
      }}
    />
  );
}
