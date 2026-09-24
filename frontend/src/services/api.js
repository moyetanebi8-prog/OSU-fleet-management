import axios from "axios";

/**
 * Shared Axios instance for all backend calls.
 * Uses relative /api/v1 so the Vite dev proxy (or a production reverse
 * proxy) routes requests to the FastAPI backend - no hardcoded backend
 * origin anywhere in the app.
 */
const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

const TOKEN_STORAGE_KEY = "fms_access_token";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

// Attach the bearer token to every request automatically.
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// A 401 means the token is missing/expired/invalid - clear it and let the
// app redirect to login rather than showing a confusing error state.
// AuthContext subscribes to this via window events instead of importing
// the router directly, keeping api.js free of React/router concerns.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      setStoredToken(null);
      window.dispatchEvent(new CustomEvent("fms:unauthorized"));
    }
    return Promise.reject(error);
  }
);

/**
 * Extracts a human-readable message from a FastAPI error response.
 * FastAPI validation errors (422) come back as {"detail": [{"msg": ...}]},
 * everything else as {"detail": "some string"}.
 */
export function getErrorMessage(error, fallback = "Something went wrong. Please try again.") {
  const detail = error?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join(" ");
  }
  return fallback;
}

export default api;
