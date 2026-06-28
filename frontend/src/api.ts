import type { VisualizeRequest, VisualizeResponse } from "./types";

// Same-origin in prod (FastAPI serves the build) and dev (Vite proxies /visualize).
export async function postVisualize(req: VisualizeRequest): Promise<VisualizeResponse> {
  const resp = await fetch("/visualize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return resp.json();
}
