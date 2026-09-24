import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

function formatDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function TripRequestCard({ request }) {
  return (
    <Link to={`/requester/requests/${request.id}`} className="card card-clickable">
      <div className="card-header">
        <h3>{request.purpose}</h3>
        <StatusBadge status={request.status} />
      </div>
      <p className="card-subtitle">{request.destination}</p>
      <div className="card-meta">
        <span>{formatDateTime(request.requested_start)}</span>
        <span>→</span>
        <span>{formatDateTime(request.requested_end)}</span>
      </div>
      <div className="card-meta">
        <span>
          {request.passenger_count} traveler{request.passenger_count === 1 ? "" : "s"}
        </span>
      </div>
      {request.status === "declined" && request.decline_reason && (
        <p className="card-decline-reason">Declined: {request.decline_reason}</p>
      )}
    </Link>
  );
}
