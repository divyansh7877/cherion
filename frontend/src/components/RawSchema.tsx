import type { VisualizeResponse } from "../types";

/** Collapsible raw response — shows the structured schema the renderer consumed. */
export default function RawSchema({ response }: { response: VisualizeResponse }) {
  return (
    <details className="raw">
      <summary>Raw response (schema)</summary>
      <pre>{JSON.stringify(response, null, 2)}</pre>
    </details>
  );
}
