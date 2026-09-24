import { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as authService from "../services/authService";
import { getStoredToken, setStoredToken } from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "loading" covers the initial "do we have a valid token?" check on
  // first load, so routes don't flash a login screen before we know.
  const [loading, setLoading] = useState(true);

  const loadCurrentUser = useCallback(async () => {
    if (!getStoredToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const currentUser = await authService.fetchCurrentUser();
      setUser(currentUser);
    } catch {
      // Token is invalid/expired - the api.js interceptor already cleared it.
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();

    // The api.js interceptor fires this on any 401 response, from any
    // request anywhere in the app - centralizes "session died" handling.
    const handleUnauthorized = () => setUser(null);
    window.addEventListener("fms:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("fms:unauthorized", handleUnauthorized);
  }, [loadCurrentUser]);

  const login = useCallback(async (username, password) => {
    const { access_token } = await authService.login(username, password);
    setStoredToken(access_token);
    const currentUser = await authService.fetchCurrentUser();
    setUser(currentUser);
    return currentUser;
  }, []);

  const logout = useCallback(() => {
    setStoredToken(null);
    setUser(null);
  }, []);

  const value = {
    user,
    loading,
    isAuthenticated: Boolean(user),
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
