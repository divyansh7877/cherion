import { useState } from "react";
import type { VisualizeResponse } from "../types";

/** Collapsible raw response — shows the structured schema the renderer consumed,
 *  with copy-to-clipboard and download-as-JSON actions. */
export default function RawSchema({ response }: { response: VisualizeResponse }) {
  const [copied, setCopied] = useState(false);
  const json = JSON.stringify(response, null, 2);

  const slug =
    response.visualization.title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "cherion-response";

  const download = () => {
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${slug}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(json);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      /* clipboard unavailable (e.g. insecure context) — ignore */
    }
  };

  return (
    <details className="raw">
      <summary>Raw response (schema)</summary>
      <div className="raw-toolbar">
        <button type="button" className="raw-btn" onClick={download}>
          ↓ Download JSON
        </button>
        <button type="button" className="raw-btn" onClick={copy}>
          {copied ? "✓ Copied" : "⧉ Copy"}
        </button>
      </div>
      <pre>{json}</pre>
    </details>
  );
}
