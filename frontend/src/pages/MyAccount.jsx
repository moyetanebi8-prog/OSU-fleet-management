import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function MyAccount() {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>My Account</h1>
          <p>Manage your personal account and security.</p>
        </div>
      </div>

      <div className="card">
        <h2>Account Information</h2>

        <div className="profile-details">
          <div>
            <strong>Username</strong>
            <span>{user.username}</span>
          </div>

          <div>
            <strong>Role</strong>
            <span className={`badge badge-role-${user.role}`}>
              {user.role}
            </span>
          </div>

          <div>
            <strong>Account Status</strong>
            <span>{user.is_active ? "Active" : "Inactive"}</span>
          </div>
        </div>

        <div className="account-actions">
          <Link to="/profile" className="btn btn-secondary">
            View Profile
          </Link>

          <Link to="/change-password" className="btn btn-primary">
            Change Password
          </Link>
        </div>
      </div>
    </section>
  );
}