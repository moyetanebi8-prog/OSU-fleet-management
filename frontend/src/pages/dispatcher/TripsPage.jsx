import { useCallback, useEffect, useState } from "react";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import LoadingSpinner from "../../components/LoadingSpinner";
import { SkeletonTable } from "../../components/Skeleton";
import MapView from "../../components/MapView";
import Modal from "../../components/Modal";
import StatusBadge from "../../components/StatusBadge";
import { useToast } from "../../context/ToastContext";
import { getErrorMessage } from "../../services/api";
import * as tripService from "../../services/tripService";

function formatDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function TripsPage() {
  const toast = useToast();
  const [trips, setTrips] = useState(null);
  const [error, setError] = useState(null);
  const [actingOnId, setActingOnId] = useState(null);
  const [routeModalTrip, setRouteModalTrip] = useState(null);
  const [routePoints, setRoutePoints] = useState([]);
  const [routeLoading, setRouteLoading] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setTrips(await tripService.listTrips());
    } catch (err) {
      setError(getErrorMessage(err, "Could not load trips."));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleStart(trip) {
    setActingOnId(trip.id);
    try {
      const updated = await tripService.startTrip(trip.id);
      setTrips((current) => current.map((t) => (t.id === updated.id ? updated : t)));
      toast.success(`Trip #${trip.id} started.`);
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not start this trip."));
    } finally {
      setActingOnId(null);
    }
  }

  async function handleComplete(trip) {
    setActingOnId(trip.id);
    try {
      const updated = await tripService.completeTrip(trip.id);
      setTrips((current) => current.map((t) => (t.id === updated.id ? updated : t)));
      toast.success(`Trip #${trip.id} completed (${updated.distance_km?.toFixed(2) ?? "0"} km).`);
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not complete this trip."));
    } finally {
      setActingOnId(null);
    }
  }

  async function handleViewRoute(trip) {
    setRouteModalTrip(trip);
    setRouteLoading(true);
    try {
      setRoutePoints(await tripService.getTripRoute(trip.id));
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not load this trip's route."));
    } finally {
      setRouteLoading(false);
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (trips === null) return <SkeletonTable rows={5} columns={7} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Trips</h1>
          <p className="page-subtitle">Active trips and trip history.</p>
        </div>
      </div>

      {trips.length === 0 ? (
        <EmptyState title="No trips yet" description="Trips appear here once a request is approved." />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Vehicle</th>
                <th>Driver</th>
                <th>Planned Start</th>
                <th>Status</th>
                <th>Distance</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {trips.map((t) => (
                <tr key={t.id}>
                  <td>#{t.id}</td>
                  <td>#{t.vehicle_id}</td>
                  <td>#{t.driver_id}</td>
                  <td>{formatDateTime(t.planned_start_time)}</td>
                  <td>
                    <StatusBadge status={t.status} />
                  </td>
                  <td>{t.distance_km != null ? `${t.distance_km.toFixed(2)} km` : "—"}</td>
                  <td className="table-actions">
                    {t.status === "approved" && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        disabled={actingOnId === t.id}
                        onClick={() => handleStart(t)}
                      >
                        Start
                      </button>
                    )}
                    {t.status === "in_progress" && (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        disabled={actingOnId === t.id}
                        onClick={() => handleComplete(t)}
                      >
                        Complete
                      </button>
                    )}
                    {(t.status === "in_progress" || t.status === "completed") && (
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => handleViewRoute(t)}
                      >
                        View route
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {routeModalTrip && (
        <Modal title={`Route for trip #${routeModalTrip.id}`} onClose={() => setRouteModalTrip(null)}>
          {routeLoading ? <LoadingSpinner label="Loading route…" /> : <MapView points={routePoints} height={320} />}
        </Modal>
      )}
    </div>
  );
}
