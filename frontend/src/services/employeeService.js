import api from "./api";

export async function searchEmployees(query = "") {
  const response = await api.get("/users/", {
    params: query ? { q: query } : undefined,
  });
  return response.data;
}
