import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from "../context/ToastContext";
import api from "../services/api";

export default function ChangePassword() {
  const navigate = useNavigate();
  const toast = useToast();

  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const [loading, setLoading] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (form.new_password.length < 8) {
      toast.error("New password must be at least 8 characters long.");
      return;
    }

    if (form.new_password !== form.confirm_password) {
      toast.error("New password and confirmation password do not match.");
      return;
    }

    setLoading(true);

    try {
      const response = await api.post("/auth/change-password", form);

      toast.success(response.data.message || "Password changed successfully.");

      setForm({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });

      navigate("/account");
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        "Could not change your password.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Change Password</h1>
          <p>Update your account password securely.</p>
        </div>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="current_password">
              Current Password
            </label>

            <input
              id="current_password"
              name="current_password"
              type="password"
              value={form.current_password}
              onChange={handleChange}
              required
              autoComplete="current-password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="new_password">
              New Password
            </label>

            <input
              id="new_password"
              name="new_password"
              type="password"
              value={form.new_password}
              onChange={handleChange}
              minLength={8}
              required
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirm_password">
              Confirm New Password
            </label>

            <input
              id="confirm_password"
              name="confirm_password"
              type="password"
              value={form.confirm_password}
              onChange={handleChange}
              minLength={8}
              required
              autoComplete="new-password"
            />
          </div>

          <div className="account-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate("/account")}
              disabled={loading}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? "Changing..." : "Change Password"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}