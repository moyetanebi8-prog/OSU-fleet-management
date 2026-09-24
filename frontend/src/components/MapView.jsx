import { MapContainer, TileLayer, Polyline, CircleMarker, Popup } from "react-leaflet";

/**
 * Renders a trip's route as a polyline, with distinct markers for the
 * start and current/end point. Uses CircleMarker instead of the default
 * Leaflet pin icon - the default icon's image paths break under most
 * bundlers (including Vite) without extra asset configuration, and a
 * circle marker looks cleaner on a route map anyway.
 */
export default function MapView({ points, height = 360 }) {
  if (!points || points.length === 0) {
    return (
      <div className="map-placeholder" style={{ height }}>
        No GPS points recorded for this trip yet.
      </div>
    );
  }

  const positions = points.map((p) => [p.lat, p.lng]);
  const start = positions[0];
  const end = positions[positions.length - 1];
  const center = positions[Math.floor(positions.length / 2)];

  return (
    <div style={{ height }} className="map-container">
      <MapContainer center={center} zoom={13} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline positions={positions} pathOptions={{ color: "#3b82f6", weight: 4 }} />
        <CircleMarker center={start} radius={8} pathOptions={{ color: "#22c55e", fillOpacity: 1 }}>
          <Popup>Start</Popup>
        </CircleMarker>
        <CircleMarker center={end} radius={8} pathOptions={{ color: "#ef4444", fillOpacity: 1 }}>
          <Popup>{points.length > 1 ? "Latest" : "Start"}</Popup>
        </CircleMarker>
      </MapContainer>
    </div>
  );
}
