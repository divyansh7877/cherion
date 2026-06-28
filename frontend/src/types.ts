// TypeScript mirror of the Cherion response schema (see SCHEMA.md).
// These types are the contract that lets the frontend render without guessing.

export type VizType =
  | "bar_chart"
  | "grouped_bar"
  | "time_series"
  | "histogram"
  | "scatter_plot"
  | "network_graph"
  | "geo_map";

export const PHASES = ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"] as const;
export const STATUSES = [
  "RECRUITING",
  "NOT_YET_RECRUITING",
  "ENROLLING_BY_INVITATION",
  "ACTIVE_NOT_RECRUITING",
  "SUSPENDED",
  "TERMINATED",
  "COMPLETED",
  "WITHDRAWN",
  "UNKNOWN",
] as const;

export interface VisualizeRequest {
  query: string;
  drug_name?: string;
  condition?: string;
  sponsor?: string;
  country?: string;
  trial_phase?: string[];
  status?: string[];
  start_year?: number;
  end_year?: number;
  max_records?: number;
}

// Structured override filters the user can set alongside the NL query.
export interface OverrideFilters {
  drug_name: string;
  condition: string;
  sponsor: string;
  country: string;
  trial_phase: string[];
  status: string[];
  start_year: string; // kept as string for input control; parsed on submit
  end_year: string;
}

export const EMPTY_FILTERS: OverrideFilters = {
  drug_name: "",
  condition: "",
  sponsor: "",
  country: "",
  trial_phase: [],
  status: [],
  start_year: "",
  end_year: "",
};

export interface Reference {
  nct_id: string;
  field: string;
  value: string;
}

export interface Channel {
  field: string;
  type: string; // nominal | ordinal | quantitative | temporal
  title?: string | null;
}

export interface Encoding {
  x?: Channel | null;
  y?: Channel | null;
  color?: Channel | null;
  size?: Channel | null;
  region?: Channel | null;
  lat?: Channel | null;
  lng?: Channel | null;
  nodes?: Record<string, string> | null;
  edges?: Record<string, string> | null;
}

// A chart datum row: known provenance fields + arbitrary dimension/metric fields.
export interface Datum {
  references: Reference[];
  total_contributors: number;
  [key: string]: unknown;
}

export interface NetworkNode {
  id: string;
  label: string;
  group: string; // drug | condition | sponsor | site
  weight: number;
  total_contributors: number;
  references: Reference[];
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
  total_contributors: number;
  references: Reference[];
}

export interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface GeoRegion {
  region: string;
  trial_count: number;
  total_contributors: number;
  references: Reference[];
}

export interface GeoPoint {
  lat: number;
  lng: number;
  label: string;
  trial_count: number;
  total_contributors: number;
  references: Reference[];
}

export interface GeoData {
  regions: GeoRegion[];
  points: GeoPoint[];
}

export interface Visualization {
  type: VizType;
  title: string;
  encoding: Encoding;
  data: Datum[] | NetworkData | GeoData;
}

export interface Meta {
  source: string;
  filters: Record<string, unknown>;
  query_interpretation: string;
  total_matching_trials: number | null;
  trials_aggregated: number | null;
  units: string | null;
  sorting: string | null;
  time_granularity: string | null;
  grouping: string | null;
  notes: string[];
  warnings: string[];
}

export interface VisualizeResponse {
  visualization: Visualization;
  meta: Meta;
}

// What the citation panel displays: a label for the clicked datum + its references.
export interface CitationSelection {
  label: string;
  totalContributors: number;
  references: Reference[];
}

export const STUDY_URL = (nct: string) => `https://clinicaltrials.gov/study/${nct}`;
