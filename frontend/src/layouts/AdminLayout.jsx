import { NavLink, Outlet } from "react-router-dom";

const TABS = [
  { to: "/admin", label: "Employees", end: true },
  { to: "/admin/users", label: "All Accounts" },
];

export default function AdminLayout() {
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
