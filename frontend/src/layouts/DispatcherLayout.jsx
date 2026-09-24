import { NavLink, Outlet } from "react-router-dom";

const TABS = [
  { to: "/dispatcher", label: "Overview", end: true },
  { to: "/dispatcher/requests", label: "Trip Requests" },
  { to: "/dispatcher/fleet", label: "Live Fleet" },
  { to: "/dispatcher/trips", label: "Trips" },
  { to: "/dispatcher/vehicles", label: "Vehicles" },
  { to: "/dispatcher/drivers", label: "Drivers" },
  { to: "/dispatcher/alerts", label: "Alerts" },
];

export default function DispatcherLayout() {
  return (
    <div className="page">
      <nav className="subnav">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) => `subnav-link${isActive ? " subnav-link-active" : ""}`}
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
