
import api from "./api";

export async function listVehicles() {
  const response = await api.get("/vehicles/");
  return response.data;
}

export async function createVehicle({ name, model, plateNumber, capacity }) {
  const response = await api.post("/vehicles/", {
    name,
    model,
    plate_number: plateNumber,
    capacity,
  });
  return response.data;
}

export async function updateVehicle(
  vehicleId,
  { name, model, plateNumber, capacity }
) {
  const response = await api.put(`/vehicles/${vehicleId}`, {
    name,
    model,
    plate_number: plateNumber,
    capacity,
  });
  return response.data;
}

export async function updateVehicleStatus(vehicleId, statusValue) {
  const response = await api.patch(`/vehicles/${vehicleId}/status`, {
    status: statusValue,
  });
  return response.data;
}

export async function deleteVehicle(vehicleId) {
  await api.delete(`/vehicles/${vehicleId}`);
}

export async function getVehicleHistory(vehicleId, limit = 200) {
  const response = await api.get(`/vehicles/${vehicleId}/history`, {
    params: { limit },
  });
  return response.data;
}

