import { useCallback, useEffect, useState } from "react";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import { SkeletonTable } from "../../components/Skeleton";
import StatusBadge from "../../components/StatusBadge";
import TripRequestReviewModal from "../../components/TripRequestReviewModal";
import { useToast } from "../../context/ToastContext";
import { getErrorMessage } from "../../services/api";
import * as tripRequestService from "../../services/tripRequestService";

function formatDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function TripRequestsPage() {
  const toast = useToast();
  const [requests, setRequests] = useState(null);
  const [error, setError] = useState(null);
  const [reviewing, setReviewing] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await tripRequestService.listTripRequests();
      setRequests(data);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load trip requests."));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleUpdated({ type }) {
    setReviewing(null);
    toast.success(type === "approved" ? "Request approved and trip created." : "Request declined.");
    load();
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (requests === null) return <SkeletonTable rows={5} columns={7} />;

  const pending = requests.filter((r) => r.status === "pending");
  const others = requests.filter((r) => r.status !== "pending");

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Trip Requests</h1>
          <p className="page-subtitle">{pending.length} pending review</p>
        </div>
      </div>

      {requests.length === 0 ? (
        <EmptyState title="No trip requests yet" description="Requests will appear here as requesters submit them." />
      ) : (
        <>
          <section className="section">
            <h2>Pending</h2>
            {pending.length === 0 ? (
              <EmptyState title="Nothing pending" description="All caught up." />
            ) : (
              <RequestsTable requests={pending} onReview={setReviewing} />
            )}
          </section>

          <section className="section">
            <h2>History</h2>
            {others.length === 0 ? (
              <EmptyState title="No decided requests yet" />
            ) : (
              <RequestsTable requests={others} />
            )}
          </section>
        </>
      )}

      {reviewing && (
        <TripRequestReviewModal
          request={reviewing}
          onClose={() => setReviewing(null)}
          onUpdated={handleUpdated}
        />
      )}
    </div>
  );
}

function RequestsTable({ requests, onReview }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Requester</th>
            <th>Destination</th>
            <th>Travelers</th>
            <th>Requested Start</th>
            <th>Requested End</th>
            <th>Status</th>
            {onReview && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {requests.map((r) => (
            <tr key={r.id}>
              <td>#{r.id}</td>
              <td>{r.requester_username}</td>
              <td>{r.destination}</td>
              <td title={r.travelers.map((t) => t.full_name).join(", ")}>
                {r.passenger_count}
              </td>
              <td>{formatDateTime(r.requested_start)}</td>
              <td>{formatDateTime(r.requested_end)}</td>
              <td>
                <StatusBadge status={r.status} />
              </td>
              {onReview && (
                <td>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => onReview(r)}>
                    Review
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
