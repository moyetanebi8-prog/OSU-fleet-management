import { useCallback, useEffect, useState } from "react";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import { SkeletonTable } from "../../components/Skeleton";
import { useWebSocket } from "../../hooks/useWebSocket";
import { getErrorMessage } from "../../services/api";
import * as alertService from "../../services/alertService";

const TYPE_LABELS = {
  SPEEDING: "Speeding",
  GEOFENCE_ENTRY: "Geofence entry",
  GEOFENCE_EXIT: "Geofence exit",
  SYSTEM: "System",
};

function formatDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("unread"); // unread | all

  const load = useCallback(async (currentFilter) => {
    setError(null);
    try {
      const data = await alertService.listAlerts(
        currentFilter === "unread" ? { isRead: false } : {}
      );
      setAlerts(data);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load alerts."));
    }
  }, []);

  useEffect(() => {
    load(filter);
  }, [load, filter]);

  // New alerts (speeding, geofence events) arrive live - prepend them
  // rather than waiting for a manual refresh.
  const handleSocketMessage = useCallback(
    (message) => {
      if (message.type === "alert") {
        setAlerts((current) => (current ? [message.data, ...current] : current));
      }
    },
    []
  );
  useWebSocket(handleSocketMessage);

  async function handleMarkRead(alert) {
    try {
      await alertService.markAlertRead(alert.id);
      setAlerts((current) => {
        if (filter === "unread") {
          return current.filter((a) => a.id !== alert.id);
        }
        return current.map((a) => (a.id === alert.id ? { ...a, is_read: true } : a));
      });
    } catch (err) {
      setError(getErrorMessage(err, "Could not mark this alert as read."));
    }
  }

  if (error) return <ErrorState message={error} onRetry={() => load(filter)} />;
  if (alerts === null) return <SkeletonTable rows={4} columns={2} />;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Alerts</h1>
          <p className="page-subtitle">Speeding and geofence events across the fleet.</p>
        </div>
        <div className="filter-toggle">
          <button
            type="button"
            className={`btn ${filter === "unread" ? "btn-secondary" : "btn-ghost"}`}
            onClick={() => setFilter("unread")}
          >
            Unread
          </button>
          <button
            type="button"
            className={`btn ${filter === "all" ? "btn-secondary" : "btn-ghost"}`}
            onClick={() => setFilter("all")}
          >
            All
          </button>
        </div>
      </div>

      {alerts.length === 0 ? (
        <EmptyState
          title={filter === "unread" ? "No unread alerts" : "No alerts yet"}
          description="You're all caught up."
        />
      ) : (
        <div className="alert-list">
          {alerts.map((alert) => (
            <div key={alert.id} className={`alert-row${alert.is_read ? "" : " alert-row-unread"}`}>
              <div>
                <span className={`badge badge-alert-${alert.type.toLowerCase()}`}>
                  {TYPE_LABELS[alert.type] || alert.type}
                </span>
                <p className="alert-message">{alert.message}</p>
                <p className="alert-meta">
                  Vehicle #{alert.vehicle_id}
                  {alert.trip_id ? ` · Trip #${alert.trip_id}` : ""} · {formatDateTime(alert.timestamp)}
                </p>
              </div>
              {!alert.is_read && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => handleMarkRead(alert)}>
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
