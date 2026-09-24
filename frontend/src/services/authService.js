import api from "./api";

/**
 * Authenticate an existing FMS user.
 *
 * FastAPI uses OAuth2PasswordRequestForm, so the login request
 * must be application/x-www-form-urlencoded.
 */
export async function login(username, password) {
  const body = new URLSearchParams();

  body.set("username", username.trim());
  body.set("password", password);

  const response = await api.post("/auth/login", body, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  return response.data;
}

/**
 * Get the currently authenticated user.
 */
export async function fetchCurrentUser() {
  const response = await api.get("/auth/me");
  return response.data;
}