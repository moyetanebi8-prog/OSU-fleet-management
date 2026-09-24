import { useState } from "react";
import Modal from "./Modal";
import { getErrorMessage } from "../services/api";
import * as driverService from "../services/driverService";

export default function AddDriverModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await driverService.createDriver({ name, licenseNumber });
      onCreated(created);
    } catch (err) {
      setError(getErrorMessage(err, "Could not add this driver."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Add driver" onClose={onClose}>
      <form onSubmit={handleSubmit} className="stacked-form">
        <label>
          Name
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />
        </label>
        <label>
          License number
          <input
            type="text"
            value={licenseNumber}
            onChange={(e) => setLicenseNumber(e.target.value)}
            required
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Adding…" : "Add driver"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
