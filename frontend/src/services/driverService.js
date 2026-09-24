import api from "./api";

export async function listDrivers() {
  const response = await api.get("/drivers/");
  return response.data;
}

export async function createDriver({ name, licenseNumber }) {
  const response = await api.post("/drivers/", { name, license_number: licenseNumber });
  return response.data;
}

export async function updateDriver(driverId, { name, licenseNumber }) {
  const response = await api.put(`/drivers/${driverId}`, { name, license_number: licenseNumber });
  return response.data;
}

export async function updateDriverStatus(driverId, statusValue) {
  const response = await api.patch(`/drivers/${driverId}/status`, { status: statusValue });
  return response.data;
}
