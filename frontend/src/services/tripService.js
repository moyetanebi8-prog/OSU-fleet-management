import api from "./api";

export async function listTrips() {
  const response = await api.get("/trips/");
  return response.data;
}

export async function getTrip(tripId) {
  const response = await api.get(`/trips/${tripId}`);
  return response.data;
}

export async function getTripRoute(tripId) {
  const response = await api.get(`/trips/${tripId}/route`);
  return response.data; // ordered list of LocationPing points for this trip
}

// --- dispatcher-only, used from Phase 15 onward ---

export async function startTrip(tripId) {
  const response = await api.post(`/trips/${tripId}/start`);
  return response.data;
}

export async function completeTrip(tripId) {
  const response = await api.post(`/trips/${tripId}/complete`);
  return response.data;
}
