
import { useState } from "react";
import Modal from "./Modal";
import { getErrorMessage } from "../services/api";
import * as vehicleService from "../services/vehicleService";

export default function AddVehicleModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [model, setModel] = useState("");
  const [plateNumber, setPlateNumber] = useState("");
  const [capacity, setCapacity] = useState(4);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const created = await vehicleService.createVehicle({
        name,
        model: model || null,
        plateNumber,
        capacity: Number(capacity),
      });

      onCreated(created);
    } catch (err) {
      setError(getErrorMessage(err, "Could not add this vehicle."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Add vehicle" onClose={onClose}>
      <form onSubmit={handleSubmit} className="stacked-form">
        <label>
          Name
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoFocus
          />
        </label>

        <label>
          Model
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="e.g. Toyota Coaster"
          />
        </label>

        <label>
          Plate number
          <input
            type="text"
            value={plateNumber}
            onChange={(e) => setPlateNumber(e.target.value)}
            required
          />
        </label>

        <label>
          Capacity
          <input
            type="number"
            min={1}
            max={100}
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
            required
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <div className="modal-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
          >
            Cancel
          </button>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
          >
            {submitting ? "Adding…" : "Add vehicle"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
