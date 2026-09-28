import { Navigate, Route, Routes } from "react-router-dom";
import AdminLayout from "../layouts/AdminLayout";
import DashboardLayout from "../layouts/DashboardLayout";
import DispatcherLayout from "../layouts/DispatcherLayout";
import Login from "../pages/Login";
import Profile from "../pages/Profile";
import MyAccount from "../pages/MyAccount";
import Settings from "../pages/Settings";
import ChangePassword from "../pages/ChangePassword";
import NotFound from "../pages/NotFound";
import RequesterDashboard from "../pages/RequesterDashboard";
import TripDetails from "../pages/TripDetails";
import AlertsPage from "../pages/dispatcher/AlertsPage";
import DispatcherOverview from "../pages/dispatcher/DispatcherOverview";
import DriversPage from "../pages/dispatcher/DriversPage";
import LiveFleetPage from "../pages/dispatcher/LiveFleetPage";
import TripRequestsPage from "../pages/dispatcher/TripRequestsPage";
import TripsPage from "../pages/dispatcher/TripsPage";
import VehiclesPage from "../pages/dispatcher/VehiclesPage";
import EmployeesPage from "../pages/admin/EmployeesPage";
import UsersPage from "../pages/admin/UsersPage";
import { useAuth } from "../context/AuthContext";
import ProtectedRoute from "./ProtectedRoute";

function HomeRedirect() {
  const { isAuthenticated, user, loading } = useAuth();
  if (loading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  const roleHome = { admin: "/admin", dispatcher: "/dispatcher", requester: "/requester" };
  return <Navigate to={roleHome[user.role] || "/requester"} replace />;
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route element={<DashboardLayout />}>
      <Route
  path="/profile"
  element={
    <ProtectedRoute>
      <Profile />
    </ProtectedRoute>
  }
/>

<Route
  path="/account"
  element={
    <ProtectedRoute>
      <MyAccount />
    </ProtectedRoute>
  }
/>

<Route
  path="/settings"
  element={
    <ProtectedRoute>
      <Settings />
    </ProtectedRoute>
  }
/>

<Route
  path="/change-password"
  element={
    <ProtectedRoute>
      <ChangePassword />
    </ProtectedRoute>
  }
/>
        <Route
          path="/requester"
          element={
            <ProtectedRoute requiredRole="requester">
              <RequesterDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/requester/requests/:requestId"
          element={
            <ProtectedRoute requiredRole="requester">
              <TripDetails />
            </ProtectedRoute>
          }
        />

        <Route
          path="/dispatcher"
          element={
            <ProtectedRoute requiredRole="dispatcher">
              <DispatcherLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DispatcherOverview />} />
          <Route path="requests" element={<TripRequestsPage />} />
          <Route path="fleet" element={<LiveFleetPage />} />
          <Route path="trips" element={<TripsPage />} />
          <Route path="vehicles" element={<VehiclesPage />} />
          <Route path="drivers" element={<DriversPage />} />
          <Route path="alerts" element={<AlertsPage />} />
        </Route>

        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="admin">
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<EmployeesPage />} />
          <Route path="users" element={<UsersPage />} />
        </Route>
      </Route>

      <Route path="/" element={<HomeRedirect />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
