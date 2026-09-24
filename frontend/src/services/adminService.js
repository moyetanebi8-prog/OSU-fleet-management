import api from "./api";

export async function createEmployee({ username, fullName, email, password }) {
  const response = await api.post("/admin/employees/", {
    username,
    full_name: fullName,
    email,
    password: password || undefined,
  });
  return response.data; // includes temporary_password if one was generated
}

export async function importEmployeesCsv(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/admin/employees/import-csv", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data; // { created: [...], errors: [...] }
}

export async function createDispatcherOrAdminAccount({ username, fullName, email, password, role }) {
  const response = await api.post("/admin/accounts/", {
    username,
    full_name: fullName,
    email,
    password,
    role,
  });
  return response.data;
}

export async function listAllUsers(role) {
  const response = await api.get("/admin/users/", {
    params: role ? { role } : undefined,
  });
  return response.data;
}

export async function updateUserStatus(userId, isActive) {
  const response = await api.patch(`/admin/users/${userId}/status`, { is_active: isActive });
  return response.data;
}
