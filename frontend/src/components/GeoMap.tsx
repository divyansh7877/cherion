import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { tokens } from "../theme";
import { STUDY_URL } from "../types";
import type { CitationSelection, GeoData, Visualization } from "../types";

interface Props {
  viz: Visualization;
  onSelect: (sel: CitationSelection) => void;
}

/** Geographic distribution: Leaflet point map + a ranked region list. */
export default function GeoMap({ viz, onSelect }: Props) {
  const geo = viz.data as GeoData;
  const max = Math.max(1, ...geo.points.map((p) => p.trial_count));

  return (
    <div>
      <MapContainer
        center={[20, 0]}
        zoom={2}
        style={{ height: 440, borderRadius: 8 }}
        worldCopyJump
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap, &copy; CARTO"
        />
        {geo.points.map((p, i) => (
          <CircleMarker
            key={i}
            center={[p.lat, p.lng]}
            radius={4 + 12 * (p.trial_count / max)}
            pathOptions={{ color: tokens.accent, fillColor: tokens.accent, fillOpacity: 0.5, weight: 1 }}
            eventHandlers={{
              click: () =>
                onSelect({
                  label: `${p.label || "site"} — ${p.trial_count} trial(s)`,
                  totalContributors: p.total_contributors,
                  references: p.references,
                }),
            }}
          >
            <Tooltip>{`${p.label || "site"}: ${p.trial_count} trial(s)`}</Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>

      <table className="region-table">
        <thead>
          <tr>
            <th>Country</th>
            <th>Trials</th>
            <th>Example study</th>
          </tr>
        </thead>
        <tbody>
          {geo.regions.slice(0, 15).map((r) => (
            <tr
              key={r.region}
              className="clickable"
              onClick={() =>
                onSelect({
                  label: `${r.region} — ${r.trial_count} trials`,
                  totalContributors: r.total_contributors,
                  references: r.references,
                })
              }
            >
              <td>{r.region}</td>
              <td>{r.trial_count}</td>
              <td>
                {r.references[0] && (
                  <a href={STUDY_URL(r.references[0].nct_id)} target="_blank" rel="noreferrer">
                    {r.references[0].nct_id}
                  </a>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
