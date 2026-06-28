// Design tokens + ECharts base options.
// Concept: monochrome "clinical instrument" UI chrome, deliberately colorful data.

export const tokens = {
  bg: "#0a0a0b",
  fg: "#f4f4f5",
  muted: "#8a8a90",
  line: "rgba(255,255,255,0.08)",
};

const MONO = "'IBM Plex Mono', ui-monospace, monospace";

// Primary color for single-series charts + map markers (the data is the color).
export const chartAccent = "#4f9dff";

// Vivid, varied palette — the color lives in the charts, not the UI.
export const palette = [
  "#4f9dff",
  "#3ddc97",
  "#ffb454",
  "#ff6b6b",
  "#c792ea",
  "#56d4dd",
  "#f78c6c",
  "#e5c07b",
];

// Per-entity colors for the network graph.
export const groupColors: Record<string, string> = {
  drug: "#4f9dff",
  condition: "#3ddc97",
  sponsor: "#c792ea",
  site: "#ffb454",
};

// Shared ECharts styling: monochrome chrome (mono font, gray axes), colorful series.
export const baseOption = {
  backgroundColor: "transparent",
  textStyle: { color: "#c9c9cf", fontFamily: MONO, fontSize: 11 },
  grid: { left: 56, right: 24, top: 28, bottom: 64, containLabel: true },
  tooltip: {
    backgroundColor: "#161617",
    borderColor: "rgba(255,255,255,0.12)",
    textStyle: { color: "#f4f4f5", fontFamily: MONO, fontSize: 12 },
  },
};

export const axisStyle = {
  axisLine: { lineStyle: { color: "rgba(255,255,255,0.16)" } },
  axisLabel: { color: "#8a8a90", fontFamily: MONO, fontSize: 11 },
  splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
  nameTextStyle: { color: "#8a8a90", fontFamily: MONO, fontSize: 11 },
};
