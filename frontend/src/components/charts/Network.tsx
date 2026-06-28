import EChart from "../EChart";
import { baseOption, groupColors, tokens } from "../../theme";
import type { CitationSelection, NetworkData, Visualization } from "../../types";

interface Props {
  viz: Visualization;
  onSelect: (sel: CitationSelection) => void;
}

/** Co-occurrence network via ECharts force-directed graph. */
export default function Network({ viz, onSelect }: Props) {
  const graph = viz.data as NetworkData;
  const groups = [...new Set(graph.nodes.map((n) => n.group))];
  const categories = groups.map((g) => ({ name: g, itemStyle: { color: groupColors[g] ?? "#888" } }));
  const catIndex = new Map(groups.map((g, i) => [g, i]));

  const maxWeight = Math.max(1, ...graph.nodes.map((n) => n.weight));

  const nodes = graph.nodes.map((n) => ({
    id: n.id,
    name: n.label,
    category: catIndex.get(n.group),
    symbolSize: 8 + 34 * Math.sqrt(n.weight / maxWeight),
    value: n.weight,
    label: { show: n.weight / maxWeight > 0.25 },
  }));

  const links = graph.edges.map((e) => ({
    source: e.source,
    target: e.target,
    value: e.weight,
    lineStyle: { width: Math.max(1, Math.min(8, e.weight)) },
  }));

  const option = {
    ...baseOption,
    grid: undefined,
    legend: { top: 0, data: groups, textStyle: { color: tokens.muted } },
    tooltip: {
      ...baseOption.tooltip,
      formatter: (p: { dataType?: string; data: { value?: number; name?: string } }) =>
        p.dataType === "edge"
          ? `${p.data.value} shared trials`
          : `${p.data.name} (${p.data.value} trials)`,
    },
    series: [
      {
        type: "graph" as const,
        layout: "force" as const,
        roam: true,
        draggable: true,
        categories,
        data: nodes,
        links,
        force: { repulsion: 180, edgeLength: [60, 160], gravity: 0.08 },
        lineStyle: { color: "#39414d", opacity: 0.6, curveness: 0.05 },
        emphasis: { focus: "adjacency" as const, lineStyle: { width: 4 } },
        label: { color: tokens.fg, fontSize: 11 },
      },
    ],
  };

  return (
    <EChart
      height={520}
      option={option}
      onDatumClick={(info) => {
        if (info.dataType === "edge") {
          const e = graph.edges[info.dataIndex];
          if (e) {
            onSelect({
              label: `${e.source.split(":").pop()} ↔ ${e.target.split(":").pop()} — ${e.weight} shared trials`,
              totalContributors: e.total_contributors,
              references: e.references,
            });
          }
          return;
        }
        const n = graph.nodes[info.dataIndex];
        if (n) {
          onSelect({
            label: `${n.group}: ${n.label} — ${n.weight} trials`,
            totalContributors: n.total_contributors,
            references: n.references,
          });
        }
      }}
    />
  );
}
