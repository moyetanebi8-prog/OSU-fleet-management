import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="page">
      <div className="empty-state">
        <h3>Page not found</h3>
        <p>The page you're looking for doesn't exist.</p>
        <Link to="/" className="btn btn-primary">
          Go home
        </Link>
      </div>
    </div>
  );
}
