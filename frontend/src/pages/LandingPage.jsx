
import { Link } from "react-router-dom";
import osuFleetLogo from "../Assets/osu-fleet-logo.png";
import heroBus from "../Assets/hero-bus.jpg";
import heroMediumBus from "../Assets/hero-medium-bus.jpg";
import heroSuv from "../Assets/hero-suv.jpg";
import {
  CalendarDays,
  CarFront,
  MapPin,
  UserRound,
} from "lucide-react";

const features = [
  {
    id: "vehicle-management",
    icon: CarFront,
    title: "Vehicle Management",
    description:
      "Keep vehicle information organized and make fleet resources easier to manage.",
  },
  {
    id: "trip-management",
    icon: CalendarDays,
    title: "Trip Management",
    description:
      "Submit transportation requests and follow the trip approval and assignment process.",
  },
  {
    id: "driver-management",
    icon: UserRound,
    title: "Driver Management",
    description:
      "Organize driver information and support clear vehicle and trip assignments.",
  },
  {
    id: "gps-tracking",
    icon: MapPin,
    title: "GPS Fleet Tracking",
    description:
      "View available fleet tracking information and monitor vehicle locations when GPS data is available.",
  },
];

export default function LandingPage() {
  return (
    <main className="landing-page">
      <header className="landing-header">
        <Link to="/" className="landing-brand">
          <img
            src={osuFleetLogo}
            alt="OSU Fleet Management System logo"
            className="landing-brand-logo"
          />
          <span>
            <strong>OSU Fleet</strong>
            <small>Management System</small>
          </span>
        </Link>

        <nav className="landing-nav" aria-label="Main navigation">
          <a href="#features">Features</a>
          <a href="#access">System Access</a>
          <a href="#about">About</a>
          <a href="#contact">Help & Contact</a>
          <Link to="/login" className="landing-nav-button">
            Sign In
          </Link>
        </nav>
      </header>

      <section className="landing-hero">
          <div className="landing-hero-content">
            <span className="landing-eyebrow">OROMIA STATE UNIVERSITY</span>

            <h1>
              Smarter Fleet Management.
              <span> Better Transportation.</span>
            </h1>

            <p>
              A centralized platform for managing university transportation
              requests, vehicles, drivers, trips, and fleet tracking information.
            </p>

            <div className="landing-hero-actions">
              <Link to="/login" className="landing-primary-button">
                Sign In to Your Account <span aria-hidden="true">→</span>
              </Link>
              <a href="#features" className="landing-secondary-button">
                Explore Features
              </a>
            </div>

            <div className="landing-trust-note">
              <span aria-hidden="true">✓</span>
              Access features based on your assigned account role.
            </div>
          </div>

          <div className="landing-hero-visual">
            <div className="landing-visual-glow" />
            <div className="landing-fleet-collage">
              <figure className="landing-fleet-photo landing-fleet-photo-suv">
                <img
                  src={heroSuv}
                  alt="Passenger SUV representing the OSU fleet"
                  fetchPriority="high"
                />
                <figcaption>
                  <span>OSU 02</span>
                </figcaption>
              </figure>
              <figure className="landing-fleet-photo landing-fleet-photo-bus">
                <img src={heroBus} alt="Coach bus representing OSU group transport" />
                <figcaption>
                  <span>OSU 01</span>
                </figcaption>
              </figure>
              <figure className="landing-fleet-photo landing-fleet-photo-medium-bus">
                <img
                  src={heroMediumBus}
                  alt="Medium-size passenger shuttle bus"
                />
                <figcaption>
                  <span>OSU 03</span>
                </figcaption>
              </figure>
              <div className="landing-fleet-caption">
                <span className="landing-live-dot" />
                <span>OROMIA STATE UNIVERSITY FLEET</span>
              </div>
            </div>
            <div className="landing-floating-badge">
              <span aria-hidden="true">✓</span>
                One platform. Multiple roles.
            </div>
          </div>
      </section>

      <section className="landing-features" id="features">
          <div className="landing-section-heading">
            <span className="landing-eyebrow">WHAT THE SYSTEM SUPPORTS</span>
            <h2>Everything organized in one place</h2>
            <p>
              Tools to support everyday university fleet and transportation
              operations.
            </p>
          </div>

          <div className="landing-feature-grid">
            {features.map((feature, index) => (
              <article
                className="landing-feature-card"
                key={feature.title}
                id={feature.id}
              >
                <div
                  className={`landing-feature-icon landing-feature-icon-${index}`}
                >
                  <feature.icon
                    size={24}
                    strokeWidth={1.8}
                    color="#2563eb"
                    aria-hidden="true"
                  />
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
                <a href={`#${feature.id}`} className="landing-feature-link">
                  Learn more <span aria-hidden="true">→</span>
                </a>
              </article>
            ))}
          </div>
      </section>

      <section className="landing-access" id="access">
          <div className="landing-section-heading">
            <span className="landing-eyebrow">SYSTEM ACCESS</span>
            <h2>Who can use this system?</h2>
            <p>
              The system provides different access according to each user's
              assigned role.
            </p>
          </div>

          <div className="landing-access-grid">
            <article className="landing-access-card">
              <div className="landing-access-icon">🛡️</div>
              <h3>Administrator</h3>
              <p>
                Manages user registration and employee records and oversees
                system access.
              </p>
              <span>Admin dashboard</span>
            </article>

            <article className="landing-access-card">
              <div className="landing-access-icon">🚚</div>
              <h3>Dispatcher</h3>
              <p>
                Manages transportation requests, vehicles, drivers, trips,
                and fleet tracking.
              </p>
              <span>Dispatcher dashboard</span>
            </article>

            <article className="landing-access-card">
              <div className="landing-access-icon">👤</div>
              <h3>Requester</h3>
              <p>
                Submits transportation requests and views their own requests.
              </p>
              <span>Requester dashboard</span>
            </article>
          </div>

          <div className="landing-registration-note">
            <div>
              <h3>Need an account?</h3>
              <p>
                Contact the OSU Fleet Management System administrator.
                Registration and account access are managed by the administrator.
              </p>
            </div>
            <Link to="/login" className="landing-primary-button">
              Sign In <span aria-hidden="true">→</span>
            </Link>
          </div>
      </section>

      <section className="landing-about" id="about">
          <div className="landing-about-mark" aria-hidden="true">
            OSU
          </div>
          <div>
            <span className="landing-eyebrow">ABOUT THE PLATFORM</span>
            <h2>Supporting organized university transportation</h2>
            <p>
              The OSU Fleet Management System brings key fleet workflows together
              in one place. It supports transportation requests, vehicle and
              driver assignments, trip records, and GPS-based fleet visibility
              for authorized users.
            </p>
          </div>
          <Link to="/login" className="landing-about-button">
            Access the System →
          </Link>
      </section>

      <section className="landing-contact" id="contact">
          <div>
            <span className="landing-eyebrow">NEED ASSISTANCE?</span>
            <h2>We're here to help you get started.</h2>
            <p>
              New users must contact the OSU Fleet Management System administrator
              to request registration. If you already have an account but cannot
              sign in, contact the system administrator for assistance.
            </p>
          </div>
          <Link to="/login" className="landing-contact-button">
            Go to Sign In
          </Link>
      </section>
      <footer className="landing-footer">
        <div className="landing-footer-main">
          <div className="landing-footer-about">
            <Link to="/" className="landing-footer-brand">
              <img src={osuFleetLogo} alt="" aria-hidden="true" />
              <span>
                <strong>OSU Fleet</strong>
                <small>Management System</small>
              </span>
            </Link>
            <p>University transportation management for Oromia State University.</p>
          </div>

          <nav className="landing-footer-nav" aria-label="Explore">
            <h2>Explore</h2>
            <a href="#features">Features</a>
            <a href="#access">System access</a>
            <a href="#about">About OSU Fleet</a>
          </nav>

          <nav className="landing-footer-nav" aria-label="Account and support">
            <h2>Account &amp; support</h2>
            <a href="#contact">Get help</a>
            <Link to="/login">Sign in</Link>
          </nav>
        </div>
        <div className="landing-footer-bottom">
          <span>© {new Date().getFullYear()} Oromia State University</span>
          <span>Access is provided according to your assigned account role.</span>
        </div>
      </footer>
    </main>
  );
}
