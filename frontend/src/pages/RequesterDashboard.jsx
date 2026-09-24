import { useCallback, useEffect, useState } from "react";
import CreateTripRequestModal from "../components/CreateTripRequestModal";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { SkeletonStatGrid } from "../components/Skeleton";
import TripRequestCard from "../components/TripRequestCard";
import { useToast } from "../context/ToastContext";
import { getErrorMessage } from "../services/api";
import * as tripRequestService from "../services/tripRequestService";
import * as tripService from "../services/tripService";

export default function RequesterDashboard() {
  const toast = useToast();
  const [requests, setRequests] = useState(null);
  const [trips, setTrips] = useState(null);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [requestsData, tripsData] = await Promise.all([
        tripRequestService.listTripRequests(),
        tripService.listTrips(),
      ]);
      setRequests(requestsData);
      setTrips(tripsData);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load your trip requests."));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleCreated(created) {
    setShowCreateModal(false);
    setRequests((current) => [created, ...(current || [])]);
    toast.success("Trip request submitted successfully.");
  }

  if (error) {
    return <ErrorState message={error} onRetry={load} />;
  }

  const loading = requests === null || trips === null;
  const pendingCount = loading ? 0 : requests.filter((r) => r.status === "pending").length;
  const approvedCount = loading ? 0 : requests.filter((r) => r.status === "approved").length;
  const activeTripCount = loading ? 0 : trips.filter((t) => t.status === "in_progress").length;
  const completedTripCount = loading ? 0 : trips.filter((t) => t.status === "completed").length;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>My Trips</h1>
          <p className="page-subtitle">Request a vehicle and track your trips.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          + New trip request
        </button>
      </div>

      {loading ? (
        <SkeletonStatGrid count={4} />
      ) : (
        <div className="stat-grid">
          <div className="stat-card">
            <span className="stat-value">{pendingCount}</span>
            <span className="stat-label">Pending Requests</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{approvedCount}</span>
            <span className="stat-label">Approved</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{activeTripCount}</span>
            <span className="stat-label">Active Trips</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{completedTripCount}</span>
            <span className="stat-label">Completed Trips</span>
          </div>
        </div>
      )}

      <section className="section">
        <h2>Your requests</h2>
        {loading ? (
          <p className="page-subtitle">Loading…</p>
        ) : requests.length === 0 ? (
          <EmptyState
            title="No trip requests yet"
            description="Create your first trip request to get a vehicle assigned."
            action={
              <button type="button" className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
                + New trip request
              </button>
            }
          />
        ) : (
          <div className="card-grid">
            {requests.map((request) => (
              <TripRequestCard key={request.id} request={request} />
            ))}
          </div>
        )}
      </section>

      {showCreateModal && (
        <CreateTripRequestModal onClose={() => setShowCreateModal(false)} onCreated={handleCreated} />
      )}
    </div>
  );
}
