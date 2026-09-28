import { useState } from "react";

export default function Settings() {
  const [notifications, setNotifications] = useState(true);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Manage your Fleet Management System preferences.</p>
        </div>
      </div>

      <div className="card">
        <h2>Notification Settings</h2>

        <div className="settings-option">
          <div>
            <strong>Notifications</strong>
            <p>
              Receive notifications about your account and system activities.
            </p>
          </div>

          <label>
            <input
              type="checkbox"
              checked={notifications}
              onChange={(event) => setNotifications(event.target.checked)}
            />
            Enable notifications
          </label>
        </div>
      </div>
    </section>
  );
}