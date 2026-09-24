import { Navigate } from "react-router-dom";
import LoadingSpinner from "../components/LoadingSpinner";
import { useAuth } from "../context/AuthContext";

/**
 * Wraps a route element, requiring authentication and (optionally) a
 * specific role. This is a UX convenience only - the backend independently
 * enforces every permission for real; a requester manually hitting a
 * dispatcher API endpoint gets rejected there regardless of what this
 * component does or doesn't render.
 */
export default function ProtectedRoute({ children, requiredRole }) {
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return (
      <div className="page-loading">
        <LoadingSpinner label="Checking your session…" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && user.role !== requiredRole) {
    const roleHome = { admin: "/admin", dispatcher: "/dispatcher", requester: "/requester" };
    return <Navigate to={roleHome[user.role] || "/requester"} replace />;
  }

  return children;
}
