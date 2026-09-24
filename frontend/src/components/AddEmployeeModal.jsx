import { useState } from "react";
import Modal from "./Modal";
import { getErrorMessage } from "../services/api";
import * as adminService from "../services/adminService";

export default function AddEmployeeModal({ onClose, onCreated }) {
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null); // set after successful creation

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await adminService.createEmployee({ username, fullName, email, password });
      setResult(created);
    } catch (err) {
      setError(getErrorMessage(err, "Could not create this employee."));
    } finally {
      setSubmitting(false);
    }
  }

  function handleDone() {
    onCreated(result);
  }

  if (result) {
    return (
      <Modal title="Employee created" onClose={handleDone}>
        <p>
          <strong>{result.full_name}</strong> ({result.username}) has been added.
        </p>
        {result.temporary_password && (
          <div className="temp-password-box">
            <p className="traveler-hint">
              One-time temporary password - record this now, it will not be shown again:
            </p>
            <code className="temp-password-value">{result.temporary_password}</code>
          </div>
        )}
        <p className="traveler-hint">
          {result.onboarding_email_sent
            ? "An onboarding email with these credentials was also sent."
            : "No onboarding email was sent (SMTP may not be configured) - relay the credentials directly."}
        </p>
        <div className="modal-actions">
          <button type="button" className="btn btn-primary" onClick={handleDone}>
            Done
          </button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title="Add employee" onClose={onClose}>
      <form onSubmit={handleSubmit} className="stacked-form">
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
          Password (optional)
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Leave blank to auto-generate one"
            minLength={8}
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Creating…" : "Create employee"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
