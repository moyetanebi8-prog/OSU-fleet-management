const STATUS_STYLES = {
  pending: { label: "Pending", className: "badge-amber" },
  approved: { label: "Approved", className: "badge-blue" },
  declined: { label: "Declined", className: "badge-red" },
  in_progress: { label: "In Progress", className: "badge-blue" },
  completed: { label: "Completed", className: "badge-green" },
  cancelled: { label: "Cancelled", className: "badge-gray" },
  available: { label: "Available", className: "badge-green" },
  assigned: { label: "Assigned", className: "badge-blue" },
  driving: { label: "Driving", className: "badge-blue" },
  maintenance: { label: "Maintenance", className: "badge-amber" },
  inactive: { label: "Inactive", className: "badge-gray" },
};

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || { label: status, className: "badge-gray" };
  return <span className={`badge ${style.className}`}>{style.label}</span>;
}
