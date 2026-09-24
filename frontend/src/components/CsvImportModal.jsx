import { useState } from "react";
import Modal from "./Modal";
import { getErrorMessage } from "../services/api";
import * as adminService from "../services/adminService";

export default function CsvImportModal({ onClose, onImported }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError("Choose a CSV file first.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const importResult = await adminService.importEmployeesCsv(file);
      setResult(importResult);
    } catch (err) {
      setError(getErrorMessage(err, "Could not import this file."));
    } finally {
      setSubmitting(false);
    }
  }

  function handleDone() {
    onImported(result);
  }

  if (result) {
    return (
      <Modal title="Import results" onClose={handleDone}>
        <p>
          {result.created.length} employee{result.created.length === 1 ? "" : "s"} created
          {result.errors.length > 0 && `, ${result.errors.length} row${result.errors.length === 1 ? "" : "s"} failed`}.
        </p>

        {result.created.length > 0 && (
          <div className="csv-result-section">
            <p className="traveler-hint">Created:</p>
            <ul className="traveler-review-list">
              {result.created.map((c) => (
                <li key={c.id}>
                  {c.full_name} ({c.username})
                  {c.temporary_password && (
                    <>
                      {" "}
                      - temp password: <code className="temp-password-value">{c.temporary_password}</code>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {result.errors.length > 0 && (
          <div className="csv-result-section">
            <p className="traveler-hint">Errors:</p>
            <ul className="csv-error-list">
              {result.errors.map((e, i) => (
                <li key={i}>
                  Row {e.row_number}: {e.error}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="modal-actions">
          <button type="button" className="btn btn-primary" onClick={handleDone}>
            Done
          </button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title="Import employees from CSV" onClose={onClose}>
      <form onSubmit={handleSubmit} className="stacked-form">
        <p className="traveler-hint">
          Required columns: <code>username, full_name, email</code>. Optional:{" "}
          <code>password</code> (auto-generated per row if omitted).
        </p>
        <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files[0] || null)} required />

        {error && <p className="form-error">{error}</p>}

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Importing…" : "Import"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
