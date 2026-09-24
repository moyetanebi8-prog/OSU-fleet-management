import api from "./api";

export async function listAlerts({ vehicleId, alertType, isRead, limit = 100 } = {}) {
  const params = {};
  if (vehicleId != null) params.vehicle_id = vehicleId;
  if (alertType) params.alert_type = alertType;
  if (isRead != null) params.is_read = isRead;
  if (limit) params.limit = limit;

  const response = await api.get("/alerts/", { params });
  return response.data;
}

export async function markAlertRead(alertId) {
  const response = await api.patch(`/alerts/${alertId}/read`);
  return response.data;
}
