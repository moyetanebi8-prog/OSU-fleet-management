import { useCallback, useEffect, useState } from "react";
import ErrorState from "../../components/ErrorState";
import { SkeletonStatGrid } from "../../components/Skeleton";
import { getErrorMessage } from "../../services/api";
import * as alertService from "../../services/alertService";
import * as driverService from "../../services/driverService";
import * as tripRequestService from "../../services/tripRequestService";
import * as tripService from "../../services/tripService";
import * as vehicleService from "../../services/vehicleService";

export default function DispatcherOverview() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [vehicles, drivers, requests, trips, unreadAlerts] = await Promise.all([
        vehicleService.listVehicles(),
        driverService.listDrivers(),
        tripRequestService.listTripRequests({ statusFilter: "pending" }),
        tripService.listTrips(),
        alertService.listAlerts({ isRead: false }),
      ]);
      setData({ vehicles, drivers, requests, trips, unreadAlerts });
    } catch (err) {
      setError(getErrorMessage(err, "Could not load fleet overview."));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <ErrorState message={error} onRetry={load} />;

  if (!data) {
    return (
      <div className="page">
        <div className="page-header">
          <div>
            <h1>Fleet Overview</h1>
            <p className="page-subtitle">Real-time snapshot of your fleet.</p>
          </div>
        </div>
        <SkeletonStatGrid count={7} />
      </div>
    );
  }

  const { vehicles, drivers, requests, trips, unreadAlerts } = data;
  const availableVehicles = vehicles.filter((v) => v.status === "available").length;
  const inTransitVehicles = vehicles.filter((v) => v.status === "in_progress").length;
  const availableDrivers = drivers.filter((d) => d.status === "available").length;
  const activeTrips = trips.filter((t) => t.status === "in_progress").length;

  const cards = [
    { label: "Total Vehicles", value: vehicles.length },
    { label: "Available Vehicles", value: availableVehicles },
    { label: "Vehicles In Transit", value: inTransitVehicles },
    { label: "Available Drivers", value: availableDrivers },
    { label: "Active Trips", value: activeTrips },
    { label: "Pending Requests", value: requests.length },
    { label: "Unread Alerts", value: unreadAlerts.length },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Fleet Overview</h1>
          <p className="page-subtitle">Real-time snapshot of your fleet.</p>
        </div>
      </div>

      <div className="stat-grid">
        {cards.map((card) => (
          <div className="stat-card" key={card.label}>
            <span className="stat-value">{card.value}</span>
            <span className="stat-label">{card.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
