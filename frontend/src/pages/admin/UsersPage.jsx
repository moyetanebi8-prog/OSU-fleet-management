import { useCallback, useEffect, useState } from "react";
import AddAccountModal from "../../components/AddAccountModal";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import { SkeletonTable } from "../../components/Skeleton";
import StatusBadge from "../../components/StatusBadge";
import { useToast } from "../../context/ToastContext";
import { getErrorMessage } from "../../services/api";
import * as adminService from "../../services/adminService";

export default function UsersPage() {
  const toast = useToast();
  const [users, setUsers] = useState(null);
  const [error, setError] = useState(null);
  const [roleFilter, setRoleFilter] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);

  const load = useCallback(async (filter) => {
    setError(null);
    try {
      setUsers(await adminService.listAllUsers(filter || undefined));
    } catch (err) {
      setError(getErrorMessage(err, "Could not load accounts."));
    }
  }, []);

  useEffect(() => {
    load(roleFilter);
  }, [load, roleFilter]);

  function handleCreated(created) {
    setShowAddModal(false);
    toast.success(`${created.full_name} added as ${created.role}.`);
    load(roleFilter);
  }

  async function handleToggleActive(user) {
    setUpdatingId(user.id);
    try {
      const updated = await adminService.updateUserStatus(user.id, !user.is_active);
      setUsers((current) => current.map((u) => (u.id === updated.id ? updated : u)));
      toast.success(`${user.full_name} is now ${updated.is_active ? "active" : "deactivated"}.`);
    } catch (err) {
      toast.error(getErrorMessage(err, "Could not update this account."));
    } finally {
      setUpdatingId(null);
    }
  }

  if (error) return <ErrorState message={error} onRetry={() => load(roleFilter)} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>All Accounts</h1>
          <p className="page-subtitle">Every user in the system, across all roles.</p>
        </div>
        <div className="table-actions">
          <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="inline-select">
            <option value="">All roles</option>
            <option value="requester">Requester</option>
            <option value="dispatcher">Dispatcher</option>
            <option value="admin">Admin</option>
          </select>
          <button type="button" className="btn btn-primary" onClick={() => setShowAddModal(true)}>
            + Add dispatcher/admin
          </button>
        </div>
      </div>

      {users === null ? (
        <SkeletonTable rows={5} columns={6} />
      ) : users.length === 0 ? (
        <EmptyState title="No accounts match this filter" />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Username</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td>
                  <td>{u.username}</td>
                  <td>{u.email || "—"}</td>
                  <td>
                    <span className={`badge badge-role-${u.role}`}>{u.role}</span>
                  </td>
                  <td>
                    <StatusBadge status={u.is_active ? "available" : "inactive"} />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      disabled={updatingId === u.id}
                      onClick={() => handleToggleActive(u)}
                    >
                      {u.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showAddModal && (
        <AddAccountModal onClose={() => setShowAddModal(false)} onCreated={handleCreated} />
      )}
    </div>
  );
}
