import { useCallback, useEffect, useMemo, useState } from "react";
import ErrorState from "../../components/ErrorState";
import FleetMapView from "../../components/FleetMapView";
import LoadingSpinner from "../../components/LoadingSpinner";
import StatusBadge from "../../components/StatusBadge";
import { useWebSocket } from "../../hooks/useWebSocket";
import { getErrorMessage } from "../../services/api";
import * as vehicleService from "../../services/vehicleService";

export default function LiveFleetPage() {
  const [vehicles, setVehicles] = useState(null);
  const [positions, setPositions] = useState({}); // vehicle_id -> { lat, lng, speed }
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const list = await vehicleService.listVehicles();
      setVehicles(list);

      // Seed initial positions from each vehicle's most recent ping.
      // N+1 calls, but fleets in this system are small enough that this
      // is simpler and more honest than inventing a bulk endpoint that
      // isn't in the spec.
      const historyResults = await Promise.all(
        list.map((v) =>
          vehicleService
            .getVehicleHistory(v.id, 1)
            .then((pings) => ({ vehicleId: v.id, ping: pings[0] || null }))
            .catch(() => ({ vehicleId: v.id, ping: null }))
        )
      );
      const seeded = {};
      for (const { vehicleId, ping } of historyResults) {
        if (ping) {
          seeded[vehicleId] = { lat: ping.lat, lng: ping.lng, speed: ping.speed };
        }
      }
      setPositions(seeded);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load the fleet."));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSocketMessage = useCallback((message) => {
    if (message.type === "location_update") {
      const { vehicle_id, lat, lng, speed } = message.data;
      setPositions((current) => ({ ...current, [vehicle_id]: { lat, lng, speed } }));
    }
  }, []);
  const wsStatus = useWebSocket(handleSocketMessage);

  const vehiclesWithPositions = useMemo(() => {
    if (!vehicles) return [];
    return vehicles.map((v) => ({ ...v, ...(positions[v.id] || {}) }));
  }, [vehicles, positions]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (vehicles === null) return <LoadingSpinner label="Loading fleet…" />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Live Fleet</h1>
          <p className="page-subtitle">
            {vehiclesWithPositions.filter((v) => v.lat != null).length} of {vehicles.length} vehicles
            reporting a position
          </p>
        </div>
        <span className={`live-indicator live-indicator-${wsStatus}`}>
          {wsStatus === "open" ? "● Live" : "○ Reconnecting…"}
        </span>
      </div>

      <FleetMapView vehicles={vehiclesWithPositions} />

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Vehicle</th>
              <th>Plate</th>
              <th>Status</th>
              <th>Speed</th>
            </tr>
          </thead>
          <tbody>
            {vehiclesWithPositions.map((v) => (
              <tr key={v.id}>
                <td>{v.name}</td>
                <td>{v.plate_number}</td>
                <td>
                  <StatusBadge status={v.status} />
                </td>
                <td>{v.speed != null ? `${v.speed.toFixed(1)} km/h` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
