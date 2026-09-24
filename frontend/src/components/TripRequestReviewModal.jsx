import { useEffect, useState } from "react";
import Modal from "./Modal";
import { getErrorMessage } from "../services/api";
import * as tripRequestService from "../services/tripRequestService";

function formatDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function TripRequestReviewModal({ request, onClose, onUpdated }) {
  const [resources, setResources] = useState(null);
  const [resourcesError, setResourcesError] = useState(null);
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const [selectedDriverId, setSelectedDriverId] = useState("");
  const [declineReason, setDeclineReason] = useState("");
  const [mode, setMode] = useState("review"); // review | decline
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    tripRequestService
      .getAvailableResources(request.id)
      .then((data) => {
        if (!cancelled) setResources(data);
      })
      .catch((err) => {
        if (!cancelled) setResourcesError(getErrorMessage(err, "Could not load available resources."));
      });
    return () => {
      cancelled = true;
    };
  }, [request.id]);

  async function handleApprove(e) {
    e.preventDefault();
    if (!selectedVehicleId || !selectedDriverId) {
      setActionError("Select a vehicle and a driver.");
      return;
    }
    setActionError(null);
    setSubmitting(true);
    try {
      await tripRequestService.approveTripRequest(
        request.id,
        Number(selectedVehicleId),
        Number(selectedDriverId)
      );
      onUpdated({ type: "approved" });
    } catch (err) {
      setActionError(getErrorMessage(err, "Could not approve this request."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDecline(e) {
    e.preventDefault();
    if (!declineReason.trim()) {
      setActionError("A reason is required to decline a request.");
      return;
    }
    setActionError(null);
    setSubmitting(true);
    try {
      await tripRequestService.declineTripRequest(request.id, declineReason.trim());
      onUpdated({ type: "declined" });
    } catch (err) {
      setActionError(getErrorMessage(err, "Could not decline this request."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title={`Review request #${request.id}`} onClose={onClose}>
      <div className="review-summary">
        <dl className="detail-list">
          <dt>Requester</dt>
          <dd>{request.requester_username}</dd>
          <dt>Purpose</dt>
          <dd>{request.purpose}</dd>
          <dt>Destination</dt>
          <dd>{request.destination}</dd>
          <dt>Start</dt>
          <dd>{formatDateTime(request.requested_start)}</dd>
          <dt>End</dt>
          <dd>{formatDateTime(request.requested_end)}</dd>
        </dl>

        <p className="traveler-hint">Travelers ({request.passenger_count}):</p>
        <ul className="traveler-review-list">
          {request.travelers.map((traveler) => (
            <li key={traveler.id}>
              {traveler.full_name}
              {traveler.id === request.requester_id && " (requester)"}
            </li>
          ))}
        </ul>
      </div>

      <div className="review-mode-toggle">
        <button
          type="button"
          className={`btn ${mode === "review" ? "btn-secondary" : "btn-ghost"}`}
          onClick={() => setMode("review")}
        >
          Approve &amp; Assign
        </button>
        <button
          type="button"
          className={`btn ${mode === "decline" ? "btn-secondary" : "btn-ghost"}`}
          onClick={() => setMode("decline")}
        >
          Decline
        </button>
      </div>

      {mode === "review" ? (
        <>
          {resourcesError && <p className="form-error">{resourcesError}</p>}
          {!resources && !resourcesError && <p className="page-subtitle">Loading available vehicles and drivers…</p>}

          {resources && (
            <form onSubmit={handleApprove} className="stacked-form">
              <label>
                Vehicle ({resources.vehicles.length} available)
                <select
                  value={selectedVehicleId}
                  onChange={(e) => setSelectedVehicleId(e.target.value)}
                  required
                >
                  <option value="" disabled>
                    Select a vehicle…
                  </option>
                  {resources.vehicles.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} — {v.plate_number} (capacity {v.capacity})
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Driver ({resources.drivers.length} available)
                <select
                  value={selectedDriverId}
                  onChange={(e) => setSelectedDriverId(e.target.value)}
                  required
                >
                  <option value="" disabled>
                    Select a driver…
                  </option>
                  {resources.drivers.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} — {d.license_number}
                    </option>
                  ))}
                </select>
              </label>

              {resources.vehicles.length === 0 && (
                <p className="form-error">No vehicles meet this request's capacity/schedule right now.</p>
              )}
              {resources.drivers.length === 0 && (
                <p className="form-error">No drivers are free for this time window.</p>
              )}

              {actionError && <p className="form-error">{actionError}</p>}

              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={onClose}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? "Approving…" : "Approve & Assign"}
                </button>
              </div>
            </form>
          )}
        </>
      ) : (
        <form onSubmit={handleDecline} className="stacked-form">
          <label>
            Reason for declining
            <textarea
              rows={3}
              value={declineReason}
              onChange={(e) => setDeclineReason(e.target.value)}
              placeholder="e.g. No vehicle available for the requested time."
              required
            />
          </label>

          {actionError && <p className="form-error">{actionError}</p>}

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-danger" disabled={submitting}>
              {submitting ? "Declining…" : "Decline request"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
