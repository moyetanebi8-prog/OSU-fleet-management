import { useState } from "react";
import Modal from "./Modal";
import { getErrorMessage } from "../services/api";
import * as adminService from "../services/adminService";

export default function AddAccountModal({ onClose, onCreated }) {
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("dispatcher");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await adminService.createDispatcherOrAdminAccount({
        username,
        fullName,
        email,
        password,
        role,
      });
      onCreated(created);
    } catch (err) {
      setError(getErrorMessage(err, "Could not create this account."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal title="Add dispatcher or admin account" onClose={onClose}>
      <form onSubmit={handleSubmit} className="stacked-form">
        <label>
          Role
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="dispatcher">Dispatcher</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <label>
          Full name
          <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} required autoFocus />
        </label>
        <label>
          Username
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} />
        </label>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Creating…" : "Create account"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
