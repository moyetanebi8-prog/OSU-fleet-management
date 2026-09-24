import { useCallback, useEffect, useState } from "react";
import AddEmployeeModal from "../../components/AddEmployeeModal";
import CsvImportModal from "../../components/CsvImportModal";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import { SkeletonTable } from "../../components/Skeleton";
import StatusBadge from "../../components/StatusBadge";
import { useToast } from "../../context/ToastContext";
import { getErrorMessage } from "../../services/api";
import * as adminService from "../../services/adminService";

function formatDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function EmployeesPage() {
  const toast = useToast();
  const [employees, setEmployees] = useState(null);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showCsvModal, setShowCsvModal] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setEmployees(await adminService.listAllUsers("requester"));
    } catch (err) {
      setError(getErrorMessage(err, "Could not load employees."));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleCreated() {
    setShowAddModal(false);
    toast.success("Employee created.");
    load();
  }

  function handleImported(result) {
    setShowCsvModal(false);
    if (result.errors.length === 0) {
      toast.success(`${result.created.length} employees imported.`);
    } else {
      toast.info(`${result.created.length} imported, ${result.errors.length} failed - see details.`);
    }
    load();
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Employees</h1>
          <p className="page-subtitle">
            {employees ? `${employees.length} employee accounts` : "Loading…"}
          </p>
        </div>
        <div className="table-actions">
          <button type="button" className="btn btn-secondary" onClick={() => setShowCsvModal(true)}>
            Import CSV
          </button>
          <button type="button" className="btn btn-primary" onClick={() => setShowAddModal(true)}>
            + Add employee
          </button>
        </div>
      </div>

      {employees === null ? (
        <SkeletonTable rows={4} columns={4} />
      ) : employees.length === 0 ? (
        <EmptyState
          title="No employees yet"
          description="Add employees one at a time, or import a CSV of your whole company."
          action={
            <button type="button" className="btn btn-primary" onClick={() => setShowAddModal(true)}>
              + Add employee
            </button>
          }
        />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Username</th>
                <th>Email</th>
                <th>Status</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((e) => (
                <tr key={e.id}>
                  <td>{e.full_name}</td>
                  <td>{e.username}</td>
                  <td>{e.email || "—"}</td>
                  <td>
                    <StatusBadge status={e.is_active ? "available" : "inactive"} />
                  </td>
                  <td>{formatDateTime(e.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAddModal && (
        <AddEmployeeModal onClose={() => setShowAddModal(false)} onCreated={handleCreated} />
      )}
      {showCsvModal && (
        <CsvImportModal onClose={() => setShowCsvModal(false)} onImported={handleImported} />
      )}
    </div>
  );
}
