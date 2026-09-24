import api from "./api";

export async function createTripRequest({ purpose, destination, travelerIds, requestedStart, requestedEnd }) {
  const response = await api.post("/trip-requests/", {
    purpose,
    destination,
    traveler_ids: travelerIds || [],
    requested_start: requestedStart,
    requested_end: requestedEnd,
  });
  return response.data;
}

export async function listTripRequests({ statusFilter } = {}) {
  const response = await api.get("/trip-requests/", {
    params: statusFilter ? { status_filter: statusFilter } : undefined,
  });
  return response.data;
}

export async function getTripRequest(requestId) {
  const response = await api.get(`/trip-requests/${requestId}`);
  return response.data;
}

// --- dispatcher-only, used from Phase 15 onward ---

export async function getAvailableResources(requestId) {
  const response = await api.get(`/trip-requests/${requestId}/available-resources`);
  return response.data;
}

export async function approveTripRequest(requestId, vehicleId, driverId) {
  const response = await api.post(`/trip-requests/${requestId}/approve`, {
    vehicle_id: vehicleId,
    driver_id: driverId,
  });
  return response.data;
}

export async function declineTripRequest(requestId, reason) {
  const response = await api.post(`/trip-requests/${requestId}/decline`, { reason });
  return response.data;
}
