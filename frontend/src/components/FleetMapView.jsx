import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";

const DEFAULT_CENTER = [0, 0]; // neutral fallback only shown when no vehicle has reported a position yet

export default function FleetMapView({ vehicles, height = 480 }) {
  const withPosition = vehicles.filter((v) => v.lat != null && v.lng != null);
  const center = withPosition.length > 0 ? [withPosition[0].lat, withPosition[0].lng] : DEFAULT_CENTER;

  return (
    <div style={{ height }} className="map-container">
      <MapContainer center={center} zoom={12} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {withPosition.map((v) => (
          <CircleMarker
            key={v.id}
            center={[v.lat, v.lng]}
            radius={9}
            pathOptions={{
              color: v.status === "in_progress" ? "#3b82f6" : "#22c55e",
              fillOpacity: 0.9,
            }}
          >
            <Popup>
              <strong>{v.name}</strong> ({v.plate_number})
              <br />
              Status: {v.status}
              <br />
              Speed: {v.speed != null ? `${v.speed.toFixed(1)} km/h` : "—"}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
