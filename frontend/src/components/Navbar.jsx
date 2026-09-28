import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  function handleLogout() {
    setMenuOpen(false);
    logout();
    navigate("/login", { replace: true });
  }

  if (!user) {
    return (
      <header className="navbar">
        <div className="navbar-brand">
          <Link to="/">Fleet Management</Link>
        </div>
      </header>
    );
  }

  const initials = user.full_name
    ?.split(" ")
    .map((name) => name[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <Link to="/">Fleet Management</Link>
      </div>

      <div className="navbar-user">
        <button
          type="button"
          className="user-menu-button"
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="user-avatar">
            {initials}
          </span>

          <span className="navbar-username">
            {user.full_name}
          </span>

          <span className={`badge badge-role-${user.role}`}>
            {user.role}
          </span>

          <span className="user-menu-arrow">
            {menuOpen ? "▲" : "▼"}
          </span>
        </button>

        {menuOpen && (
          <div className="user-dropdown">
            <Link
              to="/profile"
              onClick={() => setMenuOpen(false)}
            >
              Profile
            </Link>

            <Link
              to="/account"
              onClick={() => setMenuOpen(false)}
            >
              My Account
            </Link>

            <Link
              to="/settings"
              onClick={() => setMenuOpen(false)}
            >
              Settings
            </Link>

            <button type="button" onClick={handleLogout}>
              Log out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}