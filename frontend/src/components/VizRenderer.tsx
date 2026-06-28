import Bar from "./charts/Bar";
import GroupedBar from "./charts/GroupedBar";
import TimeSeries from "./charts/TimeSeries";
import Histogram from "./charts/Histogram";
import Scatter from "./charts/Scatter";
import Network from "./charts/Network";
import GeoMap from "./GeoMap";
import type { CitationSelection, Visualization, VizType } from "../types";

interface Props {
  viz: Visualization;
  onSelect: (sel: CitationSelection) => void;
}

const REGISTRY: Record<VizType, (p: Props) => JSX.Element> = {
  bar_chart: Bar,
  grouped_bar: GroupedBar,
  time_series: TimeSeries,
  histogram: Histogram,
  scatter_plot: Scatter,
  network_graph: Network,
  geo_map: GeoMap,
};

/** Spec-driven dispatch: pick the renderer purely from visualization.type. */
export default function VizRenderer({ viz, onSelect }: Props) {
  const Component = REGISTRY[viz.type];
  if (!Component) return <div className="warn">Unsupported visualization type: {viz.type}</div>;
  return <Component viz={viz} onSelect={onSelect} />;
}
