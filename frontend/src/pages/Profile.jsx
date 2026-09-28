import { useAuth } from "../context/AuthContext";

export default function Profile() {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>My Profile</h1>
          <p>View your Fleet Management System account information.</p>
        </div>
      </div>

      <div className="card">
        <div className="profile-avatar">
          {user.full_name?.charAt(0)?.toUpperCase()}
        </div>

        <div className="profile-details">
          <div>
            <strong>Full Name</strong>
            <span>{user.full_name}</span>
          </div>

          <div>
            <strong>Username</strong>
            <span>{user.username}</span>
          </div>

          <div>
            <strong>Email</strong>
            <span>{user.email || "Not provided"}</span>
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
      </div>
    </section>
  );
}