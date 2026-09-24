import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ErrorState from "../components/ErrorState";
import LoadingSpinner from "../components/LoadingSpinner";
import MapView from "../components/MapView";
import StatusBadge from "../components/StatusBadge";
import { useWebSocket } from "../hooks/useWebSocket";
import { getErrorMessage } from "../services/api";
import * as tripRequestService from "../services/tripRequestService";
import * as tripService from "../services/tripService";

function formatDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function TripDetails() {
  const { requestId } = useParams();

  const [request, setRequest] = useState(null);
  const [trip, setTrip] = useState(null);
  const [route, setRoute] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const requestData = await tripRequestService.getTripRequest(requestId);
      setRequest(requestData);

      if (requestData.trip_id) {
        const [tripData, routeData] = await Promise.all([
          tripService.getTrip(requestData.trip_id),
          tripService.getTripRoute(requestData.trip_id),
        ]);
        setTrip(tripData);
        setRoute(routeData);
      } else {
        setTrip(null);
        setRoute([]);
      }
    } catch (err) {
      setError(getErrorMessage(err, "Could not load this trip."));
    }
  }, [requestId]);

  useEffect(() => {
    load();
  }, [load]);

  // Live route updates while the trip is actively being tracked - refetch
  // the route whenever a GPS ping arrives for THIS trip specifically
  // (never just "this vehicle", since that could include general tracking
  // pings unrelated to this trip - see the backend's trip-association rule).
  const handleSocketMessage = useCallback(
    (message) => {
      if (message.type === "location_update" && trip && message.data.trip_id === trip.id) {
        tripService.getTripRoute(trip.id).then(setRoute).catch(() => {});
      }
    },
    [trip]
  );
  useWebSocket(trip?.status === "in_progress" ? handleSocketMessage : undefined);

  if (error) {
    return <ErrorState message={error} onRetry={load} />;
  }

  if (!request) {
    return <LoadingSpinner label="Loading trip…" />;
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>{request.purpose}</h1>
          <p className="page-subtitle">{request.destination}</p>
        </div>
        <StatusBadge status={trip ? trip.status : request.status} />
      </div>

      <section className="detail-grid">
        <div className="detail-card">
          <h2>Request</h2>
          <dl className="detail-list">
            <dt>Requested start</dt>
            <dd>{formatDateTime(request.requested_start)}</dd>
            <dt>Requested end</dt>
            <dd>{formatDateTime(request.requested_end)}</dd>
            <dt>Submitted</dt>
            <dd>{formatDateTime(request.created_at)}</dd>
          </dl>
          <p className="traveler-hint">Travelers ({request.passenger_count}):</p>
          <ul className="traveler-review-list">
            {request.travelers.map((traveler) => (
              <li key={traveler.id}>
                {traveler.full_name}
                {traveler.id === request.requester_id && " (you)"}
              </li>
            ))}
          </ul>
          {request.status === "declined" && (
            <p className="card-decline-reason">Declined: {request.decline_reason}</p>
          )}
        </div>

        {trip && (
          <div className="detail-card">
            <h2>Trip</h2>
            <dl className="detail-list">
              <dt>Vehicle</dt>
              <dd>#{trip.vehicle_id}</dd>
              <dt>Driver</dt>
              <dd>#{trip.driver_id}</dd>
              <dt>Planned start</dt>
              <dd>{formatDateTime(trip.planned_start_time)}</dd>
              <dt>Planned end</dt>
              <dd>{formatDateTime(trip.planned_end_time)}</dd>
              <dt>Actual start</dt>
              <dd>{formatDateTime(trip.actual_start_time)}</dd>
              <dt>Actual end</dt>
              <dd>{formatDateTime(trip.actual_end_time)}</dd>
              {trip.distance_km != null && (
                <>
                  <dt>Distance</dt>
                  <dd>{trip.distance_km.toFixed(2)} km</dd>
                </>
              )}
            </dl>
          </div>
        )}
      </section>

      {trip && (trip.status === "in_progress" || trip.status === "completed") && (
        <section className="section">
          <h2>Route</h2>
          <MapView points={route} />
        </section>
      )}
    </div>
  );
}
