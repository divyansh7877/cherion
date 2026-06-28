// Design tokens + ECharts base options shared across chart components.

export const tokens = {
  bg: "#0b0f14",
  panel: "#141b24",
  panelAlt: "#0f151d",
  line: "#243040",
  fg: "#e6edf3",
  muted: "#8b98a5",
  accent: "#4493f8",
  warn: "#f0b429",
};

// Per-entity colors for the network graph + a categorical palette for series.
export const groupColors: Record<string, string> = {
  drug: "#4493f8",
  condition: "#3fb950",
  sponsor: "#db61a2",
  site: "#f0b429",
};

export const palette = [
  "#4493f8",
  "#3fb950",
  "#db61a2",
  "#f0b429",
  "#a371f7",
  "#f78166",
  "#56d4dd",
  "#e3b341",
];

// Shared ECharts styling so every chart looks consistent on the dark theme.
export const baseOption = {
  backgroundColor: "transparent",
  textStyle: { color: tokens.fg, fontFamily: "ui-sans-serif, system-ui, sans-serif" },
  grid: { left: 56, right: 24, top: 28, bottom: 64, containLabel: true },
  tooltip: {
    backgroundColor: tokens.panel,
    borderColor: tokens.line,
    textStyle: { color: tokens.fg },
  },
};

export const axisStyle = {
  axisLine: { lineStyle: { color: tokens.line } },
  axisLabel: { color: tokens.muted },
  splitLine: { lineStyle: { color: tokens.line, opacity: 0.4 } },
  nameTextStyle: { color: tokens.muted },
};
