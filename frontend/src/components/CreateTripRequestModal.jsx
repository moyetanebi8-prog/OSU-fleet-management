import { useState } from "react";
import Modal from "./Modal";
import TravelerSelector from "./TravelerSelector";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../services/api";
import * as tripRequestService from "../services/tripRequestService";

export default function CreateTripRequestModal({ onClose, onCreated }) {
  const { user } = useAuth();

  const [purpose, setPurpose] = useState("");
  const [destination, setDestination] = useState("");
  const [travelerIds, setTravelerIds] = useState([]); // OTHER travelers - requester is implicit
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!start || !end) {
      setError("Please choose a start and end time.");
      return;
    }
    if (new Date(end) <= new Date(start)) {
      setError("End time must be after start time.");
      return;
    }

    setSubmitting(true);
    try {
      const created = await tripRequestService.createTripRequest({
        purpose,
        destination,
        travelerIds,
        requestedStart: new Date(start).toISOString(),
        requestedEnd: new Date(end).toISOString(),
      });
      onCreated(created);
    } catch (err) {
      setError(getErrorMessage(err, "Could not submit your request."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="New trip request" onClose={onClose}>
      <form onSubmit={handleSubmit} className="stacked-form">
        <label>
          Purpose
          <input
            type="text"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            placeholder="e.g. Client site visit"
            required
            autoFocus
          />
        </label>

        <label>
          Destination
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="e.g. Downtown office"
            required
          />
        </label>

        <div className="form-row">
          <label>
            Start
            <input
              type="datetime-local"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              required
            />
          </label>

          <label>
            End
            <input
              type="datetime-local"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              required
            />
          </label>
        </div>

        <TravelerSelector
          requesterName={user?.full_name || "You"}
          selectedIds={travelerIds}
          onChange={setTravelerIds}
        />

        {error && <p className="form-error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Submitting…" : "Submit request"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
