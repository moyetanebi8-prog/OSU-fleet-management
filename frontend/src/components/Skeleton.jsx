export function SkeletonStatGrid({ count = 4 }) {
  return (
    <div className="stat-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div className="stat-card skeleton-card" key={i}>
          <div className="skeleton-block skeleton-block-lg" />
          <div className="skeleton-block skeleton-block-sm" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 4, columns = 4 }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r}>
              {Array.from({ length: columns }).map((_, c) => (
                <td key={c}>
                  <div className="skeleton-block skeleton-block-cell" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
