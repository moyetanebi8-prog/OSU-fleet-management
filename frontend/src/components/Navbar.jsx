import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <Link to="/">Fleet Management</Link>
      </div>

      {user && (
        <div className="navbar-user">
          <span className="navbar-username">{user.full_name}</span>
          <span className={`badge badge-role-${user.role}`}>{user.role}</span>
          <button type="button" className="btn btn-ghost" onClick={handleLogout}>
            Log out
          </button>
        </div>
      )}
    </header>
  );
}
