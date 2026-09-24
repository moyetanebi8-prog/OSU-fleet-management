import { useCallback, useEffect, useState } from "react";
import AddVehicleModal from "../../components/AddVehicleModal";
import ConfirmDialog from "../../components/ConfirmDialog";
import EditVehicleModal from "../../components/EditVehicleModal";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import { SkeletonTable } from "../../components/Skeleton";
import StatusBadge from "../../components/StatusBadge";
import { useToast } from "../../context/ToastContext";
import { getErrorMessage } from "../../services/api";
import * as vehicleService from "../../services/vehicleService";

// Only statuses a dispatcher can set by hand - `assigned`/`in_progress`
// are set exclusively by the trip workflow, and the backend rejects any
// attempt to set them manually with a 409. Matching that here means the
// dropdown never offers an option that would just fail.
const MANUAL_STATUSES = ["available", "maintenance", "inactive"];

export default function VehiclesPage() {
  const toast = useToast();
  const [vehicles, setVehicles] = useState(null);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(null);
  const [deletingVehicle, setDeletingVehicle] = useState(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setVehicles(await vehicleService.listVehicles());
    } catch (err) {
      setError(getErrorMessage(err, "Could not load vehicles."));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleCreated(created) {
    setShowAddModal(false);
    setVehicles((current) => [...(current || []), created]);
    toast.success(`Vehicle "${created.name}" added.`);
  }

  function handleUpdated(updated) {
    setEditingVehicle(null);
    setVehicles((current) => current.map((v) => (v.id === updated.id ? updated : v)));
    toast.success(`${updated.name} updated.`);
  }

  async function handleStatusChange(vehicle, newStatus) {
    setUpdatingId(vehicle.id);
    try {
      const updated = await vehicleService.updateVehicleStatus(vehicle.id, newStatus);
      setVehicles((current) => current.map((v) => (v.id === updated.id ? updated : v)));
      toast.success(`${vehicle.name} is now ${newStatus}.`);
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not change vehicle status."));
    } finally {
      setUpdatingId(null);
    }
  }

  async function handleDelete() {
    if (!deletingVehicle) return;
    setDeleteSubmitting(true);
    try {
      await vehicleService.deleteVehicle(deletingVehicle.id);
      setVehicles((current) => current.filter((v) => v.id !== deletingVehicle.id));
      toast.success(`${deletingVehicle.name} removed.`);
      setDeletingVehicle(null);
    } catch (err) {
      // Most likely a 409: the backend blocks deleting a vehicle with
      // trip/GPS history via a real foreign-key constraint, not just an
      // app-side check - surface that reason instead of a generic failure.
      toast.error(getErrorMessage(err, "Could not delete this vehicle."));
    } finally {
      setDeleteSubmitting(false);
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Vehicles</h1>
          <p className="page-subtitle">{vehicles ? `${vehicles.length} in the fleet` : "Loading…"}</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setShowAddModal(true)}>
          + Add vehicle
        </button>
      </div>

      {vehicles === null ? (
        <SkeletonTable rows={4} columns={5} />
      ) : vehicles.length === 0 ? (
        <EmptyState
          title="No vehicles yet"
          description="Add your first vehicle to start assigning trips."
          action={
            <button type="button" className="btn btn-primary" onClick={() => setShowAddModal(true)}>
              + Add vehicle
            </button>
          }
        />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Model</th>
                <th>Plate</th>
                <th>Capacity</th>
                <th>Status</th>
                <th>Change status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {vehicles.map((v) => (
                <tr key={v.id}>
                 <td>{v.name}</td>
                 <td>{v.model || "—"}</td>
                  <td>{v.plate_number}</td>
                  <td>{v.capacity}</td>
                  <td>
                    <StatusBadge status={v.status} />
                  </td>
                  <td>
                    {MANUAL_STATUSES.includes(v.status) ? (
                      <select
                        value={v.status}
                        disabled={updatingId === v.id}
                        onChange={(e) => handleStatusChange(v, e.target.value)}
                        className="inline-select"
                      >
                        {MANUAL_STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="table-muted">on an active trip</span>
                    )}
                  </td>
                  <td className="table-actions">
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => setEditingVehicle(v)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => setDeletingVehicle(v)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAddModal && (
        <AddVehicleModal onClose={() => setShowAddModal(false)} onCreated={handleCreated} />
      )}

      {editingVehicle && (
        <EditVehicleModal
          vehicle={editingVehicle}
          onClose={() => setEditingVehicle(null)}
          onUpdated={handleUpdated}
        />
      )}

      {deletingVehicle && (
        <ConfirmDialog
          title="Delete vehicle"
          message={`Remove "${deletingVehicle.name}" (${deletingVehicle.plate_number})? Vehicles with trip or GPS history can't be deleted - you'll get an error if this one has any, and can mark it "inactive" instead.`}
          confirmLabel="Delete"
          danger
          submitting={deleteSubmitting}
          onConfirm={handleDelete}
          onClose={() => setDeletingVehicle(null)}
        />
      )}
    </div>
  );
}
