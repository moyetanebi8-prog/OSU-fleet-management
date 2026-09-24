import { useCallback, useEffect, useState } from "react";
import AddDriverModal from "../../components/AddDriverModal";
import EditDriverModal from "../../components/EditDriverModal";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import { SkeletonTable } from "../../components/Skeleton";
import StatusBadge from "../../components/StatusBadge";
import { useToast } from "../../context/ToastContext";
import { getErrorMessage } from "../../services/api";
import * as driverService from "../../services/driverService";

// `assigned`/`driving` are set exclusively by the trip workflow - see
// VehiclesPage's comment, same reasoning applies here.
const MANUAL_STATUSES = ["available", "inactive"];

export default function DriversPage() {
  const toast = useToast();
  const [drivers, setDrivers] = useState(null);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingDriver, setEditingDriver] = useState(null);
  const [updatingId, setUpdatingId] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setDrivers(await driverService.listDrivers());
    } catch (err) {
      setError(getErrorMessage(err, "Could not load drivers."));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleCreated(created) {
    setShowAddModal(false);
    setDrivers((current) => [...(current || []), created]);
    toast.success(`Driver "${created.name}" added.`);
  }

  function handleUpdated(updated) {
    setEditingDriver(null);
    setDrivers((current) => current.map((d) => (d.id === updated.id ? updated : d)));
    toast.success(`${updated.name} updated.`);
  }

  async function handleStatusChange(driver, newStatus) {
    setUpdatingId(driver.id);
    try {
      const updated = await driverService.updateDriverStatus(driver.id, newStatus);
      setDrivers((current) => current.map((d) => (d.id === updated.id ? updated : d)));
      toast.success(`${driver.name} is now ${newStatus}.`);
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not change driver status."));
    } finally {
      setUpdatingId(null);
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Drivers</h1>
          <p className="page-subtitle">{drivers ? `${drivers.length} on staff` : "Loading…"}</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setShowAddModal(true)}>
          + Add driver
        </button>
      </div>

      {drivers === null ? (
        <SkeletonTable rows={4} columns={4} />
      ) : drivers.length === 0 ? (
        <EmptyState
          title="No drivers yet"
          description="Add your first driver to start assigning trips."
          action={
            <button type="button" className="btn btn-primary" onClick={() => setShowAddModal(true)}>
              + Add driver
            </button>
          }
        />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>License</th>
                <th>Status</th>
                <th>Change status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {drivers.map((d) => (
                <tr key={d.id}>
                  <td>{d.name}</td>
                  <td>{d.license_number}</td>
                  <td>
                    <StatusBadge status={d.status} />
                  </td>
                  <td>
                    {MANUAL_STATUSES.includes(d.status) ? (
                      <select
                        value={d.status}
                        disabled={updatingId === d.id}
                        onChange={(e) => handleStatusChange(d, e.target.value)}
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
                      onClick={() => setEditingDriver(d)}
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAddModal && <AddDriverModal onClose={() => setShowAddModal(false)} onCreated={handleCreated} />}

      {editingDriver && (
        <EditDriverModal
          driver={editingDriver}
          onClose={() => setEditingDriver(null)}
          onUpdated={handleUpdated}
        />
      )}
    </div>
  );
}
