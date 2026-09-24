import api from "./api";

export async function listGeofences() {
  const response = await api.get("/geofences/");
  return response.data;
}

export async function createGeofence({ name, description, coordinates }) {
  const response = await api.post("/geofences/", { name, description, coordinates });
  return response.data;
}
