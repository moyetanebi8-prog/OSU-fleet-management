import { useEffect, useRef, useState } from "react";
import { searchEmployees } from "../services/employeeService";

/**
 * Lets a requester pick which employees are traveling with them.
 * The requester themselves is always shown as "You" and is never part of
 * `selectedIds` - the backend adds the requester as a traveler
 * automatically (see trip_service.create_trip_request_with_travelers), so
 * the frontend only ever needs to send the OTHER travelers' ids.
 */
export default function TravelerSelector({ requesterName, selectedIds, onChange }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]); // [{id, full_name}, ...]
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(async () => {
      setLoading(true);
      try {
        const employees = await searchEmployees(query);
        setResults(employees);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => window.clearTimeout(debounceRef.current);
  }, [query]);

  function toggleEmployee(employee) {
    const alreadySelected = selectedIds.includes(employee.id);
    if (alreadySelected) {
      onChange(selectedIds.filter((id) => id !== employee.id));
      setSelectedEmployees((current) => current.filter((e) => e.id !== employee.id));
    } else {
      onChange([...selectedIds, employee.id]);
      setSelectedEmployees((current) => [...current, employee]);
    }
  }

  function removeEmployee(employeeId) {
    onChange(selectedIds.filter((id) => id !== employeeId));
    setSelectedEmployees((current) => current.filter((e) => e.id !== employeeId));
  }

  return (
    <div className="traveler-selector">
      <label htmlFor="traveler-search">Who is going with you?</label>
      <input
        id="traveler-search"
        type="text"
        placeholder="Search employees…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoComplete="off"
      />

      {query.trim() !== "" && (
        <div className="traveler-results">
          {loading && <p className="traveler-hint">Searching…</p>}
          {!loading && results.length === 0 && <p className="traveler-hint">No matching employees.</p>}
          {!loading &&
            results.map((employee) => (
              <label key={employee.id} className="traveler-result-row">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(employee.id)}
                  onChange={() => toggleEmployee(employee)}
                />
                {employee.full_name}
              </label>
            ))}
        </div>
      )}

      <div className="traveler-selected">
        <p className="traveler-hint">Selected travelers:</p>
        <ul className="traveler-chip-list">
          <li className="traveler-chip traveler-chip-self">{requesterName} (You)</li>
          {selectedEmployees.map((employee) => (
            <li key={employee.id} className="traveler-chip">
              {employee.full_name}
              <button
                type="button"
                className="traveler-chip-remove"
                onClick={() => removeEmployee(employee.id)}
                aria-label={`Remove ${employee.full_name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
        <p className="traveler-hint">Total travelers: {selectedIds.length + 1}</p>
      </div>
    </div>
  );
}
