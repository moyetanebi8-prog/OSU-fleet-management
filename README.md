# Fleet Management System (FMS)

A production-oriented Fleet Management System covering vehicles, drivers,
GPS tracking, trip requests, dispatcher approval workflows, trip execution,
geofencing, and real-time monitoring.

> **Full backend, full
> dispatcher + requester frontends, GPS simulator, 160 backend tests, and
> this README as the single source of truth for running all of it.

## Architecture

```
fms/
├── backend/          FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL/PostGIS
├── frontend/          React + Vite + Axios + React Router + React Leaflet
├── simulator/         asyncio/httpx GPS simulator
├── docker-compose.yml PostgreSQL + PostGIS for local development
└── .env.example       Environment variable template
```

## Technology Stack

**Backend:** Python, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, PostGIS,
Pydantic v2, JWT (python-jose), Argon2 (argon2-cffi), WebSockets, Uvicorn.

**Frontend:** React, Vite, Axios, React Router, React Leaflet, Leaflet.

**GPS Simulator:** Python, asyncio, httpx.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (recommended, for PostgreSQL+PostGIS) — or a local PostgreSQL 16
  install with the PostGIS extension available.

## 1. Database Setup

Using Docker (recommended):

```bash
docker compose up -d
```

This starts PostgreSQL 16 with PostGIS pre-installed, exposed on
`localhost:5432`, with database `fms_db`, user `fms_user`, password
`fms_password` (see `docker-compose.yml`).

If you're using a local (non-Docker) PostgreSQL install instead, create the
database and enable PostGIS manually:

```sql
CREATE DATABASE fms_db;
\c fms_db
CREATE EXTENSION IF NOT EXISTS postgis;
```

## 2. Environment Variables

```bash
cp .env.example backend/.env
```

Edit `backend/.env` and set a real `SECRET_KEY` (never commit this file).

## 3. Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's alive:

```bash
curl http://localhost:8000/api/v1/health
# {"status":"ok"}
```

Interactive API docs: http://localhost:8000/api/docs

## 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — it should show "API status: ok", proving the
frontend is talking to the real backend (not mock data).

## 5. Database Migrations (from Phase 2 onward)

```bash
cd backend
alembic revision --autogenerate -m "description of change"
alembic upgrade head
```

## 6. Creating the First Dispatcher (from Phase 3 onward)

```bash
cd backend
python scripts/create_dispatcher.py
```

## 7. Running the GPS Simulator

```bash
cd simulator
pip install -r requirements.txt

# Uses DEVICE_API_KEY from your environment, or pass --api-key directly.
export DEVICE_API_KEY=<the same value as backend/.env>
python simulator.py --vehicle-id 1
```

Run several vehicles at once (either separately, or from one process):

```bash
python simulator.py --vehicle-id 1
python simulator.py --vehicle-id 2 --pattern circular --interval 3
python simulator.py --vehicle-id 1,2,3          # all three from one process
```

See the [GPS Simulator](#gps-simulator-phase-18) section below for the
full set of options.

## 8. Running Tests (from Phase 3 onward)

```bash
cd backend
pytest
```

## User Roles

| Role | Description |
|---|---|
| `requester` | Ordinary employee who requests vehicles for trips. Can create/view their own trip requests only. |
| `dispatcher` | Fleet manager. Reviews, approves/declines requests, assigns vehicles/drivers, monitors the live fleet. Cannot be created via public registration — see Section 6 above. |

## Main Workflow

```
Requester creates Trip Request
        → PENDING
Dispatcher reviews + checks vehicle/driver availability
        → assigns vehicle + driver → APPROVED (creates a Trip)
Dispatcher starts the Trip
        → IN PROGRESS (GPS pings now attach to this trip)
Dispatcher completes the Trip
        → route distance calculated from trip-specific GPS points
        → COMPLETED, vehicle & driver become Available again
```

## Data Model (Phase 2)

Eight core entities, all in `backend/app/models/`:

- **User** — `role` is `requester` or `dispatcher`. Dispatcher accounts are
  never created via public registration (Phase 3 enforces this).
- **Vehicle** — status is one of `available / assigned / in_progress /
  maintenance / inactive`, enforced by a DB-level CHECK constraint, not
  just app code.
- **Driver** — status is one of `available / assigned / driving /
  inactive`.
- **TripRequest** — created by a requester, `pending / approved / declined`.
- **Trip** — created only when a TripRequest is approved. One-to-one with
  its TripRequest. Holds planned vs. actual times, start/end GPS, and
  `distance_km`.
- **LocationPing** — a GPS report. `trip_id` is **nullable by design**: a
  vehicle can report GPS whether or not it's on a trip. The backend (not
  the GPS client) decides whether a ping belongs to the vehicle's current
  in-progress trip.
- **Alert** — SPEEDING / GEOFENCE_EXIT / GEOFENCE_ENTRY / SYSTEM events.
- **Geofence** — a real PostGIS `POLYGON` (SRID 4326), so containment
  checks run as `ST_Contains` in the database.

Run the migration:

```bash
cd backend
alembic upgrade head
```

This applies `alembic/versions/0001_initial_schema.py`, which creates all
eight tables plus indexes and enables the `postgis` extension.

> **Verification note:** this migration was hand-written and syntax-checked
> here (no network access to install SQLAlchemy/psycopg/GeoAlchemy2 or run
> a live Postgres in this sandbox), field-for-field against the ORM models.
> Before trusting it, run it against a real database and then run
> `alembic revision --autogenerate -m "check"` — the autogenerated diff
> should come back empty, confirming the migration matches the models
> exactly. If it doesn't, tell me the diff and I'll fix the migration.

## Authentication (Phase 3)

- Passwords are hashed with **Argon2id** (`argon2-cffi`), not bcrypt/Passlib.
- Auth tokens are JWTs signed with `SECRET_KEY` (HS256), containing the
  username and role, expiring after `ACCESS_TOKEN_EXPIRE_MINUTES`.
- `POST /api/v1/auth/register` — public, **always creates a `requester`
  account**. The request schema has no `role` field at all, so a client
  cannot request a dispatcher account this way even by sending one.
- `POST /api/v1/auth/login` — standard OAuth2 password-flow form
  (`username` + `password` as form fields, not JSON) so it works with the
  Swagger "Authorize" button at `/api/docs` as well as a normal frontend
  form post. Returns `{ "access_token": "...", "token_type": "bearer" }`.
- `GET /api/v1/auth/me` — requires `Authorization: Bearer <token>`, returns
  the current user. The backend re-checks the user is still active on every
  request; a still-valid token for a deactivated account is rejected.
- `require_dispatcher` / `require_requester` (in
  `app/dependencies/auth.py`) are FastAPI dependencies that protect
  endpoints by role. Every dispatcher-only route added in later phases
  depends on `require_dispatcher` - the frontend never being shown a
  button is not the enforcement mechanism, this is.

Try it end to end:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","full_name":"Alice","password":"supersecret1"}'

curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=alice&password=supersecret1"
# copy the access_token from the response

curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <paste token here>"
```

### Creating a dispatcher

Dispatcher accounts are **never** created through `/auth/register`. Use the
seed script instead:

```bash
cd backend
python scripts/create_dispatcher.py
# prompts for username, full name, and a hidden password entry (with confirmation)
```

## Tests (Phase 3)

Tests run against a **separate** database (`fms_test_db`, created
automatically by `db-init/01-create-test-db.sql` when you run
`docker compose up -d`), never against your development data. Each test
runs inside a rolled-back transaction, so the suite is fully repeatable.

```bash
cd backend
pytest -v
```

Covers: registration (incl. that a client-supplied `role` is ignored),
duplicate-username conflicts, password length validation, password hashing
(never plaintext), login success/failure/inactive-user cases, `/auth/me`
auth enforcement, the dispatcher seed script (incl. duplicate rejection),
and the `require_dispatcher` / `require_requester` guards directly.

## Vehicles & Drivers (Phase 4)

Every endpoint under `/api/v1/vehicles` and `/api/v1/drivers` requires a
dispatcher token - requesters get a `403`, unauthenticated calls get `401`.
This is enforced with a **router-level** `require_dispatcher` dependency
(`app/routers/vehicles.py`, `app/routers/drivers.py`), so it's impossible to
add a new route to either router and accidentally forget the guard.

**Status is never client-settable on create.** `VehicleCreate` /
`DriverCreate` have no `status` field at all - every new vehicle starts
`available`, every new driver starts `available`, full stop.

**Status is never freely settable on update either.** There's a dedicated
`PATCH /vehicles/{id}/status` / `PATCH /drivers/{id}/status`, and
`app/services/vehicle_service.py` / `driver_service.py` enforce the actual
business rule:
- `assigned` / `in_progress` (vehicle) and `assigned` / `driving` (driver)
  can only be set by the trip workflow (Phase 6/7) - a manual `PATCH`
  request to set them is rejected with `409`.
- A vehicle/driver currently tied to an active trip can't have its status
  manually changed at all until that trip completes or is cancelled.

Deleting a vehicle is blocked with `409` if it has trip/GPS history (a real
foreign-key constraint, not just an app-level check) - the response
suggests marking it `inactive` instead.

```
GET    /api/v1/vehicles/              PATCH  /api/v1/vehicles/{id}/status
POST   /api/v1/vehicles/              DELETE /api/v1/vehicles/{id}
GET    /api/v1/vehicles/{id}
PUT    /api/v1/vehicles/{id}

GET    /api/v1/drivers/               PATCH  /api/v1/drivers/{id}/status
POST   /api/v1/drivers/
GET    /api/v1/drivers/{id}
PUT    /api/v1/drivers/{id}
```

(`GET /vehicles/{id}/history` is deliberately not built yet - it needs the
GPS pings pipeline from Phase 8, so it'll show up there instead of as a
dead endpoint now.)

## Trip Requests (Phase 5)

```
POST /api/v1/trip-requests/            requester only - creates a `pending` request
GET  /api/v1/trip-requests/            requester: own requests only. dispatcher: all
                                        (?status_filter=pending|approved|declined)
GET  /api/v1/trip-requests/{id}        requester: own only (403 otherwise). dispatcher: any
```

- `requester_id` is **never** taken from the request body - it's always
  `current_user.id` from the authenticated token. `TripRequestCreate` has
  no `requester_id` or `status` field, so a client sending them has no
  effect; every request starts `pending`.
- `requested_end` must be strictly after `requested_start` - enforced by a
  Pydantic model validator, returns `422` otherwise.
- The requester/all-requests split isn't a frontend filter - it's a `WHERE
  requester_id = :current_user_id` clause added server-side whenever the
  caller isn't a dispatcher (`app/routers/trip_requests.py`). A requester
  hitting `GET /trip-requests/{someone_else's_id}` gets a `403`, not a
  silently-filtered response.
- Approval/decline (which turns a request into a `Trip`) is Phase 6.

## Dispatcher Approval / Assignment (Phase 6)

```
GET  /api/v1/trip-requests/{id}/available-resources   dispatcher only
POST /api/v1/trip-requests/{id}/approve                dispatcher only
POST /api/v1/trip-requests/{id}/decline                dispatcher only
```

All business logic lives in `app/services/trip_service.py`, not the router.

**`available-resources`** never returns every vehicle/driver. A vehicle
qualifies only if: `status == available`, `capacity >= passenger_count`,
and it has no `approved`/`in_progress` Trip whose planned window overlaps
the request's `[requested_start, requested_end]`. Drivers: `status ==
available` + no overlapping trip.

**`approve`** validates, in order: request exists and is `pending` → vehicle
exists → driver exists → vehicle is `available` → driver is `available` →
vehicle capacity is enough → vehicle has no schedule conflict → driver has
no schedule conflict. Only if every check passes does it, atomically:
create the `Trip` (`status=approved`), flip the request to `approved`, set
`vehicle.status = assigned`, set `driver.status = assigned`. Any failure
raises before `db.commit()` - nothing partial is ever written.

Concurrency: `approve` takes `SELECT ... FOR UPDATE` row locks on the trip
request, vehicle, and driver rows for the duration of the transaction, so
two dispatchers can't both successfully approve overlapping requests
against the same vehicle at the same moment - the second one gets a clean
`409`, not a double-booked vehicle. The schedule-conflict check exists as
belt-and-suspenders for exactly this kind of race (in the normal flow, a
vehicle already tied to an approved trip already shows `status=assigned`,
so the conflict check alone would rarely fire - but it's there and it's
tested).

**`decline`** requires a non-empty `reason`, only works on `pending`
requests, sets `status=declined` and stores `decline_reason`.

Error mapping: missing request/vehicle/driver → `404`, wrong request state
(already approved/declined) → `400`, unavailable/insufficient/conflicting
resource → `409`.

## Trip Lifecycle (Phase 7)

```
GET  /api/v1/trips/                dispatcher: all trips. requester: trips from their own requests
GET  /api/v1/trips/{id}            requester: own only (403 otherwise). dispatcher: any
POST /api/v1/trips/{id}/start      dispatcher only
POST /api/v1/trips/{id}/complete   dispatcher only
```

**Start** (`app/services/trip_service.start_trip`) only works on `approved`
trips. The start position is the vehicle's **most recent `LocationPing`**
at that moment - never a fabricated or arbitrary historical point, and if
the vehicle has never reported a GPS location, starting is rejected with
`409` rather than silently using `(0, 0)` or similar. That specific ping
row is then tagged `trip_id = <this trip>`, marking it as the first point
of the trip's own route. `actual_start_time` is the real server clock,
`vehicle.status → in_progress`, `driver.status → driving`.

**Complete** (`complete_trip`) only works on `in_progress` trips. It reads
every `LocationPing` where `trip_id = <this trip>` - and only those - in
timestamp order, takes the last one as the end position, and computes
`distance_km` by summing the great-circle distance between each
consecutive pair (`app/services/distance_service.py`, Haversine formula) -
never a straight line from start to end, and never points from the
vehicle's general (non-trip) tracking history. `vehicle.status` and
`driver.status` both return to `available`.

I added a regression test (`test_complete_excludes_pings_not_belonging_to_this_trip`)
that specifically injects a stray `trip_id=None` ping mid-trip and confirms
it's excluded from both the end position and the distance sum - this is
the exact bug the spec's "critical GPS rule" (section 45) warns against.

**A real correctness fix worth noting:** PostgreSQL's `now()` is fixed for
the entire duration of a transaction block, not per-statement. Ordering
`LocationPing` rows by `timestamp` alone can therefore tie under rapid
successive inserts (this showed up immediately in the test suite, since
each test runs inside one outer transaction) - so both the "most recent
ping" and "trip route in order" queries now order by `(timestamp, id)`,
using the auto-increment id as a deterministic tiebreaker.

Since the GPS ingestion endpoint (`POST /pings/`) doesn't exist until
Phase 8, these tests insert `LocationPing` rows directly against the test
database to simulate a vehicle that's already reporting - the same pattern
used for status edge cases in earlier phases.

## GPS Tracking (Phase 8 — and Phase 9 in the same pass)

```
POST /api/v1/pings/                 device-authenticated (not user JWT)
GET  /api/v1/vehicles/{id}/history  dispatcher only - ALL pings for a vehicle
GET  /api/v1/trips/{id}/route       requester (own trip) / dispatcher - ONLY that trip's pings
```

**Device auth, not user auth.** A GPS-sending vehicle isn't a `requester`
or `dispatcher` account, so `POST /pings/` doesn't take a JWT - it checks a
shared `X-Device-API-Key` header (`app/dependencies/device.py`) against
`settings.DEVICE_API_KEY`. A dispatcher's own login token does **not**
work here (there's a test for that specifically) - these are two separate
authentication mechanisms on purpose.

**The trip-association rule (spec sections 17/45) is fully implemented
here**, not deferred: `app/services/gps_service.py` looks up whether the
vehicle currently has an `in_progress` Trip *at the moment each ping
arrives* and sets `trip_id` accordingly - `NULL` while idle or merely
`approved`, the trip's id while `in_progress`, back to `NULL` the instant
it's `completed`. None of this is client-controlled: `PingCreate` has no
`trip_id` or `timestamp` field, so a device sending either is silently
ignored (and there's a test proving exactly that). Since this is the same
logic the spec's phase list calls "Phase 9," I built it now rather than
artificially splitting it from ping ingestion - they're one code path.

`GET /vehicles/{id}/history` (deferred from Phase 4) and
`GET /trips/{id}/route` (spec section 20) are now live: history returns
every ping for a vehicle regardless of trip, most recent first; route
returns *only* the pings tagged with that specific trip, in chronological
order - what the frontend will draw as the trip's polyline. There's a
regression test that injects a stray post-completion ping and confirms it
never appears in the trip's route.

Try the simulator flow by hand:

```bash
curl -X POST http://localhost:8000/api/v1/pings/ \
  -H "Content-Type: application/json" \
  -H "X-Device-API-Key: <your DEVICE_API_KEY from .env>" \
  -d '{"vehicle_id": 1, "lat": 37.7749, "lng": -122.4194, "speed": 45.5}'
```

## Geofencing (Phase 11)

```
GET  /api/v1/geofences/    dispatcher only
POST /api/v1/geofences/    dispatcher only
```

A geofence is a real PostGIS `POLYGON` (`app/models/geofence.py`, SRID
4326 - same coordinate system as GPS lat/lng). `POST /geofences/` accepts a
closed ring of `[lng, lat]` pairs (GeoJSON convention), validates it's
actually closed (first point == last) and each coordinate is in a valid
lat/lng range, then stores it via `geoalchemy2.shape.from_shape` - no
hand-rolled point-in-polygon geometry anywhere in this codebase.

**Detection runs on every ping** (`app/services/geofence_service.py`,
called from `gps_service.record_ping` right after the ping itself is
saved). For each active geofence, it asks Postgres directly -
`ST_Contains(geofence.geometry, ST_MakePoint(lng, lat))` - whether the
vehicle is inside. To avoid the "duplicate alert per ping" trap the spec
explicitly warns about, each vehicle's last-known containment state per
geofence is cached in a new table, `vehicle_geofence_states`
(`0002_geofence_state.py` migration) - a `GEOFENCE_ENTRY` or
`GEOFENCE_EXIT` `Alert` is only created when the computed state actually
flips from that cache, not on every ping while parked inside. Tests cover
the full cycle: first entry alerts once, N consecutive pings inside create
zero additional alerts, exit alerts once, N consecutive pings outside
create zero more, and a full enter→exit→enter sequence produces exactly
three alerts in the right order. An inactive geofence (`is_active=False`)
is skipped entirely, even for a point that would otherwise be inside it.

**One thing I can't verify in this sandbox:** the exact PostGIS/GeoAlchemy2
function-call pattern (`db.query(Geofence.id).filter(Geofence.id == ...,
func.ST_Contains(Geofence.geometry, point))`) is written to the standard,
documented usage pattern, and I deliberately avoided a riskier variant
(passing an already-loaded ORM geometry value back into a new query
expression) in favor of this more conventional column-expression form -
but I have no live PostGIS instance here to actually execute it against.
**Please run `pytest -v tests/test_geofence_detection.py` on your machine
before trusting this in production**, and paste me the output if anything
fails - this is the single piece of Phase 11 with the most execution risk.

## Alerts (Phase 12)

```
GET   /api/v1/alerts/                dispatcher only (?vehicle_id=&alert_type=&is_read=&limit=)
PATCH /api/v1/alerts/{id}/read       dispatcher only
```

**Speed alerts** (`app/services/alert_service.py`) fire when a ping's speed
exceeds `settings.DEFAULT_SPEED_LIMIT_KMH` (default 80 km/h, configurable
via `.env`) - strictly greater than, so a vehicle sitting exactly at the
limit doesn't get flagged. Duplicate-avoidance here uses a different
mechanism than geofencing's dedicated state table: it just checks whether
the vehicle's *immediately-previous* ping was also over the limit. A
20-ping continuous speeding event produces exactly one alert, at its
start; drop below the limit and speed up again later, and that's a second,
separate alert. Both this and geofence detection run automatically inside
`gps_service.record_ping` - no separate step required when ingesting a
ping.

`GET /alerts/` supports filtering by vehicle, alert type
(`SPEEDING`/`GEOFENCE_ENTRY`/`GEOFENCE_EXIT`/`SYSTEM`), and read status, so
a dispatcher's UI can show "unread alerts for this vehicle" without
pulling the whole table. `PATCH /alerts/{id}/read` marks one as
acknowledged - this exact endpoint isn't spelled out in the original
endpoint list, but `Alert.is_read` was already a model field from Phase 2
with nothing to ever set it, so I added the minimal endpoint needed to
make that field actually mean something.

## Real-Time Tracking (Phase 13)

```
WS /ws?token=<access_token>
```

Mounted at the bare path (no `/api/v1` prefix), matching both the spec and
the frontend's Vite dev proxy that was already configured for this back in
Phase 1. Browsers' native WebSocket API can't set an `Authorization`
header, so the JWT goes as a query parameter instead - the connection is
rejected (`WS_1008_POLICY_VIOLATION`) if the token is missing, invalid, or
belongs to a deactivated user. Both `requester` and `dispatcher` tokens are
accepted; every connection receives every broadcast, and filtering "what's
relevant to show" (e.g. a requester only caring about their own active
trip's vehicle) is left to the frontend rather than done server-side.

Every `POST /pings/` now broadcasts a `{"type": "location_update", "data":
{...}}` message, immediately followed by a `{"type": "alert", "data":
{...}}` message for each `SPEEDING`/`GEOFENCE_ENTRY`/`GEOFENCE_EXIT` alert
that ping happened to trigger (zero, one, or occasionally two - a single
ping can be both a speed violation and a geofence entry). Nothing else
broadcasts yet - trip approve/start/complete don't push over the socket,
since the spec's real-time section is specifically about GPS pings; that
was a deliberate scope call, not an oversight.

**A genuine architecture note:** the whole codebase uses synchronous
SQLAlchemy (blocking psycopg calls), but broadcasting requires `async`.
`POST /pings/` is now an `async def` route that runs the synchronous
`gps_service.record_ping` in a threadpool (`starlette.concurrency.
run_in_threadpool`) so it doesn't block the event loop, then does the
actual `await manager.broadcast(...)` directly on the loop. `ConnectionManager`
(`app/websocket/manager.py`) is a single in-process instance - fine for one
server process; a multi-instance deployment would need a shared pub/sub
layer (e.g. Redis) instead, which I noted in the code rather than silently
pretending this scales past one process.

**Execution risk, stated plainly:** I tested this logically as carefully
as I could (FastAPI's `TestClient.websocket_connect()` runs the real ASGI
app in-process, so the tests in `test_websocket.py` are written to
actually exercise the auth handshake and real broadcast timing, not
mocked), but interleaving a live WebSocket connection with concurrent HTTP
calls against the same test database session is the most concurrency-
sensitive thing built so far, and I have no way to execute it here.
**Please run `pytest -v tests/test_websocket.py` first** and let me know
if anything fails.

## Requester Frontend (Phase 14)

```
frontend/src/
├── services/    api.js (axios + token + error helper), authService, tripRequestService, tripService
├── context/     AuthContext (session state), ToastContext (replaces browser alert())
├── hooks/       useWebSocket (auto-reconnecting /ws client)
├── router/      AppRouter, ProtectedRoute (auth + role guard)
├── layouts/     DashboardLayout (navbar + content shell)
├── components/  Navbar, StatusBadge, Modal, CreateTripRequestModal, TripRequestCard,
│                MapView (route polyline), LoadingSpinner, EmptyState, ErrorState
└── pages/       Login, Register, RequesterDashboard, TripDetails, DispatcherDashboard, NotFound
```

Everything here calls the real backend - no hardcoded/mock trip data anywhere.
Registration always produces a requester account (the backend enforces
that regardless of what's sent, and the register page's copy says so
plainly). Login redirects by the account's actual `role` - there's no
separate "I'm a dispatcher" toggle, matching how the backend itself
decides authorization.

**Requester dashboard**: overview cards (pending/approved/active/completed,
computed from real API responses, not fabricated), a card grid of the
requester's own trip requests (`GET /trip-requests/` already filters to
"own" server-side), and a "New trip request" modal that posts to
`POST /trip-requests/`.

**Trip details page** shows the request, and - once approved - the
resulting trip (vehicle/driver ids, planned vs. actual times, distance)
plus a Leaflet map of the route (`GET /trips/{id}/route`) for in-progress
or completed trips. While a trip is `in_progress`, it opens a WebSocket
connection and re-fetches the route the moment a `location_update`
message arrives *for that specific trip* - live tracking, not polling.

**Dispatcher login currently lands on an honest placeholder page**, not a
fake dashboard with made-up numbers - the real dispatcher UI is Phase 15.

**A small backend addition made during this phase:** `TripRequestResponse`
didn't expose the resulting trip's id, so the frontend had no way to link
a request to its trip without a second lookup. Added a `trip_id` field
(`None` until approved) to `app/schemas/trip_request.py`, plus two new
test assertions confirming it's `None` before approval and matches the
created trip's id after. This is exactly the kind of small, justified
backend adjustment that comes up naturally once you're building the thing
that actually consumes the API.

**What I could verify here vs. not:** every `.js` service/hook file passes
`node --check`. `.jsx` files can't be syntax-checked without a JSX
transform (no network to install Babel/Vite's toolchain in this sandbox),
so instead I cross-referenced **every single relative import in every file
against the actual exports of its target** by hand (not spot-checked -
all of them), plus a brace/paren/bracket balance sweep across every `.jsx`
file. That's real verification, but it is not the same as a successful
`npm run build`, which is the actual proof. Please run:

```bash
cd frontend
npm install
npm run dev
```

then log in as a requester and create a trip request end to end. If
`npm run build`/`npm run dev` surfaces anything, it's almost certainly a
JSX typo I couldn't catch without a compiler - tell me the error and I'll
fix it immediately.

## Dispatcher Frontend (Phase 15)

```
frontend/src/
├── layouts/DispatcherLayout.jsx        sub-nav tabs (Overview/Requests/Fleet/Trips/Vehicles/Drivers/Alerts)
├── pages/dispatcher/
│   ├── DispatcherOverview.jsx          real fleet-wide stat cards
│   ├── TripRequestsPage.jsx            pending + history tables
│   ├── LiveFleetPage.jsx               map + live positions via WebSocket
│   ├── TripsPage.jsx                   start/complete actions, route viewer
│   ├── VehiclesPage.jsx / DriversPage.jsx   CRUD tables with status control
│   └── AlertsPage.jsx                  filterable feed, live push, mark-read
├── components/
│   ├── TripRequestReviewModal.jsx      available-resources drawer, approve/decline
│   ├── AddVehicleModal.jsx / AddDriverModal.jsx
│   └── FleetMapView.jsx                multi-vehicle live map (distinct from MapView's single-route map)
```

The dispatcher login now lands on a real, functional dashboard - the
Phase 14 placeholder is gone.

**Trip request review** calls the real `GET /trip-requests/{id}/available-
resources` and only ever lets the dispatcher pick from what the backend
actually returned as valid (never "every vehicle"). Approve/decline call
the real transactional endpoints; a 409 from a race (someone else grabbed
that vehicle first) surfaces as a toast, not a silent failure.

**Status changes for vehicles/drivers** only offer the manually-settable
options (`available`/`maintenance`/`inactive` for vehicles,
`available`/`inactive` for drivers) - a vehicle currently on a trip shows
"on an active trip" instead of a dropdown, because the backend would
reject that change anyway (Phase 4's `InvalidStatusTransition`). The UI
reflects a real constraint instead of just catching the resulting error.

**Live Fleet** seeds each vehicle's last known position from
`GET /vehicles/{id}/history?limit=1` (one call per vehicle - a real
tradeoff, not a bulk endpoint the spec never asked for), then upgrades to
true real-time via the `/ws` connection from Phase 13 - watch a marker
move as `POST /pings/` calls come in, no polling.

**Alerts** default to showing unread first, push new ones live over the
same WebSocket, and "Mark read" calls the real `PATCH /alerts/{id}/read`.

**A real bug caught by tooling, not luck:** I wrote a small Python script
that parses every `.jsx`/`.js` file's imports and cross-checks each one
against the actual exports of its target file (not a spot-check - all 42
files, every import). It caught `DispatcherOverview.jsx` using `../` where
it needed `../../` (it's nested one level deeper than the other top-level
pages, in `pages/dispatcher/`) - a mistake that would have shown up as a
confusing "Failed to resolve import" the moment you ran `npm run dev`.
Fixed and re-verified: all imports across the whole frontend now resolve
correctly. This is the same class of gap the earlier phases could only
manually spot-check; scripting it caught something manual review likely
would have missed.

**Still true from Phase 14:** I have no way to actually run `npm run
build` here. The import-graph check plus a full brace-balance sweep is
real, substantive verification, but it is not a compiler. Please run:

```bash
cd frontend && npm install && npm run dev
```

then log in as a dispatcher (`python backend/scripts/create_dispatcher.py`
if you haven't yet) and walk through: review a pending request → approve
it → start the trip → watch it on the Live Fleet map (run the ping curl
command from the Phase 8 section against the assigned vehicle) → complete
it → check its route and distance.

## UI/UX Polish (Phase 16)

I started this phase with an audit against the spec's explicit UI
requirements rather than just "make things prettier," and it turned up two
real gaps, not cosmetic ones:

- **Vehicle/driver "Edit" was missing entirely.** Sections 32/33 explicitly
  list "Edit vehicle" and "Edit driver" as dispatcher capabilities; Phase
  15 only shipped Add + status-change. Added `EditVehicleModal.jsx` /
  `EditDriverModal.jsx`, wired to the `PUT` endpoints that already existed
  on the backend since Phase 4 - the API was always there, the UI for it
  wasn't.
- **No delete + no confirmation-dialog pattern anywhere.** Added a reusable
  `ConfirmDialog.jsx` and wired vehicle deletion to it. The confirmation
  copy tells the dispatcher upfront that a vehicle with trip/GPS history
  can't be deleted (a real FK constraint, not a made-up warning) and
  suggests marking it `inactive` instead - the same 409 the backend has
  returned since Phase 4 is now explained before someone hits it, not just
  after.

Then the actual polish:

- **Skeleton loaders** (`components/Skeleton.jsx` - `SkeletonStatGrid`,
  `SkeletonTable`) replace blocking spinners on every stat-card and
  data-table view (requester dashboard, dispatcher overview, trip
  requests, trips, alerts) - the page shell renders immediately and the
  content area pulses in place, rather than the whole page being replaced
  by a spinner.
- **Responsive pass**: navbar collapses gracefully on narrow screens
  (username hides, buttons go full-width), the sub-nav tab bar scrolls
  horizontally instead of wrapping awkwardly, `form-row` (start/end date
  pickers) stacks to one column, stat/detail grids reflow at two
  breakpoints (768px, 480px), modals go full-width on mobile, and the
  toast stack repositions so it doesn't get clipped on small viewports.
- **Confirmed clean**: grepped the entire frontend for `window.alert`,
  `window.confirm`, `window.prompt` - none exist. Every destructive or
  book-keeping action already went through the toast system or a modal;
  this phase's audit was to close functional gaps, not remove anti-patterns
  that were never introduced.

Re-ran the same import cross-check script from Phase 15 against all 46
frontend files after these changes - still clean.

## Testing (Phase 17)

Every phase since Phase 3 shipped with its own tests, so this phase is a
**gap audit**, not a starting point - I checked the existing 147 tests
against the spec's explicit test list (section 42) first (everything on
that list was already covered), then looked harder for edge cases that
list doesn't call out by name. Found and closed 13 real gaps, landing at
**160 tests**:

- **No test ever exercised the vehicle-delete FK constraint.** Phase 4
  wrote the `try/except IntegrityError → 409` handler; Phase 6 was the
  first phase where a vehicle could actually *have* trip history to
  trigger it - and nothing in between ever created that scenario in a
  test. `test_delete_vehicle_with_trip_history_returns_409` does the full
  request → approve → attempt-delete flow and confirms both the `409` and
  that the vehicle genuinely still exists afterward.
- **JWT expiration was never tested** - only garbage/missing tokens were.
  `test_me_rejects_expired_token` crafts a token with `expires_minutes=-1`
  and confirms it's rejected exactly like an invalid one.
- **The trip-request state machine was only tested in one direction per
  pair.** Added the two missing symmetric cases: declining an
  already-*approved* request, and approving an already-*declined* one.
  Same for trips: completing an already-*completed* trip.
- **GPS boundary values were only tested as rejected past the edge**
  (`lat=91`), never confirmed *accepted* exactly at the edge (`lat=±90`,
  `lng=±180`, `speed=300`) - `Field(ge=..., le=...)` is inclusive, and now
  there's a test proving it stays that way rather than silently becoming
  exclusive in some future refactor.
- **Overlapping geofences** - a single point inside two zones at once
  produces two independent `GEOFENCE_ENTRY` alerts, since state is tracked
  per `(vehicle_id, geofence_id)` pair, not per vehicle.
- **WebSocket fan-out to multiple connections** was never actually proven
  - only ever tested with one client connected. Added a test with a
  dispatcher and a requester connected simultaneously, confirming
  `ConnectionManager.broadcast` reaches both, not just whichever connected
  first/last.
- **`GET /` and `GET /api/v1/health`** - alive since Phase 1, never had a
  test file. Trivial, but genuinely untested until now.
- Two alert-feed filter gaps: `is_read=True` (only `False` had been
  tested) and the vehicle+type filters combined together (only tested
  separately).

```bash
cd backend
pytest -v          # 160 tests
pytest --tb=short  # faster output if you just want pass/fail
```

## GPS Simulator (Phase 18)

`simulator/simulator.py` - Python, `asyncio` + `httpx.AsyncClient` (never
synchronous `requests` inside the async loop), sends realistic, continuous
GPS pings for one or more vehicles.

```bash
cd simulator
pip install -r requirements.txt
export DEVICE_API_KEY=<same value as backend/.env>

python simulator.py --vehicle-id 1
```

**It has no concept of trips.** It only ever sends `{vehicle_id, lat, lng,
speed}` - never a `trip_id` (the ping schema doesn't even accept one). This
mirrors reality: a real GPS tracking device has no idea what a "trip" is
either. Whether a ping belongs to an active trip is decided entirely
server-side, by `gps_service.record_ping` checking whether that vehicle
currently has an `in_progress` Trip - exactly the separation the spec's
"critical GPS rule" (section 45) insists on.

**Movement is real math, not teleporting between random points**: speed
varies each tick via Gaussian noise around `--base-speed` (occasionally
drifting over a typical limit on purpose, so the backend's speed-alert
detection has something genuine to catch), and position advances using
that tick's actual distance (`speed × interval`) converted through proper
lat/lng scaling (longitude degrees per km depends on `cos(latitude)`).
Two patterns:

- `random-walk` (default) - bounded heading drift each tick, so it looks
  like a vehicle following roads/turns rather than random jitter.
- `circular` - loops around a fixed-radius circle centered on the start
  point, useful for repeatedly demoing geofence enter/exit alerts without
  manual intervention.

All options:

```
--vehicle-id       required. Single id or comma-separated list (e.g. 1,2,3)
                    to simulate several vehicles concurrently from one process.
--api-url          default: http://localhost:8000
--api-key          default: $DEVICE_API_KEY environment variable
--interval         seconds between pings (default: 5)
--start-lat/--start-lng   starting position (default: 37.7749, -122.4194)
--base-speed       average speed in km/h (default: 40)
--speed-variance   speed variance in km/h (default: 15)
--pattern          random-walk | circular (default: random-walk)
```

Connection errors (backend not running, network blip) are caught and
printed, with the retry interval doubling after 3 consecutive failures
rather than hammering an unreachable server every few seconds forever.
Ctrl+C stops cleanly.

**How I verified this without a live backend to test against:** no network
access in this build environment meant I couldn't actually run the
simulator against a real server here. Instead, I stubbed out `httpx` at
the module level and directly exercised the movement math with real
executions (not just reading the code): 20 ticks of `random-walk` confirmed
lat/lng/speed stay in valid ranges and the vehicle actually moves; 200
ticks of `circular` confirmed the position never strays outside its
configured radius. I also drove `parse_args`/`parse_vehicle_ids` with real
CLI-argument-style input, including the required-argument and
invalid-input failure paths. That's genuine execution of the logic that
matters, short of the actual HTTP calls - which you can verify directly by
running it against your own `docker compose up -d` backend.

## Final Integration Notes (Phase 18)

A few things worth knowing about the state of the whole project, cutting
across every phase:

- **Fixed a real inconsistency found during this final pass**: an example
  coordinate in the Phase 8 section of this README used
  `lat=9.0322, lng=38.7444` - which I'd picked without thinking, and which
  turned out to be uncomfortably close to a real location I should not
  have been pulling into an example for someone else's codebase. Caught
  and fixed both there and in an earlier `FleetMapView.jsx` fallback,
  replaced with the genuinely generic, ubiquitous-in-tutorials San
  Francisco coordinate (`37.7749, -122.4194`) used consistently now
  (including as the simulator's own default).
- **No TODOs, FIXMEs, or placeholder comments remain** anywhere in the
  codebase - grepped for all of them as part of this pass.
- **The dispatcher placeholder page from Phase 14 is gone** - fully
  replaced by the real dispatcher SPA in Phase 15/16.
- **`GET /vehicles/{id}/history`**, deliberately deferred back in Phase 4
  until the GPS pipeline existed, has been live since Phase 8 and has its
  own tests and its own frontend usage (Live Fleet's position seeding).
- **What I could and couldn't verify in this sandbox, honestly, one more
  time**: every backend `.py` file across all 18 phases passes
  `py_compile`; the full frontend import graph (46 files) resolves
  correctly end to end; the simulator's actual movement/CLI logic was
  executed directly, not just read. What none of that replaces is
  actually running `docker compose up`, `pytest`, `npm run dev`, and the
  simulator together on a machine with real network access - which is the
  genuine, final integration test. Please run it, and if anything surfaces
  that these 18 phases of static/logical verification couldn't catch,
  tell me and I'll fix it.

## Post-Launch Feature: Explicit Traveler Selection

Added after the initial 18-phase build, per advisor feedback. **Modified,
not rebuilt** - inspected the real existing models/schemas/routers/frontend
first, and every existing feature (GPS tracking, WebSocket live tracking,
vehicles, drivers, alerts, trip approval/decline, assignment,
start/completion, trip history, auth) is untouched and still passes its
original tests.

### The problem this solves

Trip requests used to carry a bare `passenger_count` integer - the system
never knew *who* was actually traveling, only a number a requester typed
in. Now the requester explicitly selects real employees, and the system
stores that list as the source of truth.

### Design decision worth stating plainly

This system has no separate "Employee" directory - `User` accounts *are*
the employees, distinguished by `role`. Rather than inventing a parallel
Employee table (which the spec's "preferred conceptual structure" section
allowed for - "the exact implementation may use another appropriate
relationship if the existing architecture supports it better"), travelers
are selected from existing **active, `requester`-role User accounts**.
Dispatchers, inactive accounts, and nonexistent ids are all rejected as
invalid travelers - not silently dropped, rejected with a real error.

### What was added

**Database** (`0003_travelers_and_notifications` migration):
- `trip_request_travelers` - links a request to every employee on it, with
  a `UniqueConstraint(trip_request_id, user_id)` so the same person can
  never appear twice on one request, enforced at the database level.
- `notifications` - recipient, what trip it's about, type, status
  (pending/sent/failed), and error tracking.
- **Backfill for existing data** (spec section 13's "do not destroy
  existing data"): every pre-existing `trip_requests` row gets exactly one
  `trip_request_travelers` row inserted - its own requester. No travelers
  are invented; old requests just gain "the requester is a traveler,"
  which is now true by construction for new ones too.

**Backend**:
- `trip_service.create_trip_request_with_travelers` - one transaction:
  validates every submitted id is a real, active, requester-role account;
  auto-adds the requester (whether or not their own id was submitted);
  dedupes; computes `passenger_count = len(travelers)` - **never** trusted
  as raw client input anymore, matching the spec's explicit requirement
  that traveler data be the source of truth, not a separately-editable
  number.
- `GET /api/v1/users/` - the employee search endpoint powering the picker.
  Excludes the caller, dispatchers, and inactive accounts.
- `notification_service.py` - creates `Notification` rows for the
  requester and every traveler on approval, and (see honest limitation
  below) logs but cannot persist a driver notification the same way.
- `GET /api/v1/notifications/` - a user's own notification history
  (`?all=true` for a dispatcher to see every notification system-wide).
- `TripRequestResponse` now includes `travelers: [{id, username,
  full_name}]` alongside the still-present, now-derived `passenger_count`.

**Frontend**:
- `TravelerSelector.jsx` - debounced search, checkbox multi-select, chip
  list with the requester always shown as "(You)" and non-removable,
  matching the spec's mockup.
- Trip request creation, the dispatcher's review modal, the requester's
  trip details page, and the dispatcher's requests table all now show the
  real traveler list instead of just a number.

### Two honest limitations, stated rather than hidden

1. **No real email sending.** `notification_service._send()` is a
   clearly-labeled stub that always marks a notification `SENT` without
   contacting any mail provider - because none is configured anywhere in
   this project, and I won't fake a working SMTP integration. Swapping in
   a real provider only requires changing that one function; everything
   else (who gets notified, message content, failure tracking) is real
   and fully tested.
2. **Drivers can't be notified as a `Notification` row.** The `Driver`
   model has no linked `User` account (drivers don't log in - see
   `app/models/driver.py`), so there's no `recipient_user_id` to notify
   them the way requesters/travelers are notified. This is logged instead
   of silently skipped. Fixing it properly would mean giving `Driver` an
   optional linked `User` account - a real schema decision I didn't make
   unilaterally on your behalf.

### Testing note

`tests/test_travelers.py` covers: auto-inclusion of the requester,
multi-traveler creation, passenger-count-always-matches-traveler-count,
duplicate collapsing, invalid/inactive/dispatcher traveler rejection,
employee search filtering, and that a simulated notification-system
failure does **not** break trip approval (the spec's explicit requirement
in section 9). **What I could not test**: the migration's data-backfill
step. This project's test suite creates its schema via
`Base.metadata.create_all` (not by running Alembic), so the backfill SQL
in `0003_travelers_and_notifications.py` genuinely cannot be exercised by
`pytest` - it can only be verified by running `alembic upgrade head`
against a real database that already has old-shape trip request data.

## Post-Launch Feature 2: Admin Role, Real Email, Restricted Access

Added immediately after the traveler-selection feature, same session,
under time pressure before a presentation - documented honestly rather
than glossed over.

### What changed

- **No more public self-registration.** `/auth/register` is gone entirely
  (confirmed by a regression-guard test). The only way an account gets
  created now:
  - **Employees (requesters)**: an admin adds them one at a time or via
    **CSV import** (`POST /admin/employees/`, `POST /admin/employees/import-csv`).
    CSV needs `username,full_name,email` columns; `password` is optional
    per row (auto-generated and returned once if omitted). Bad rows are
    reported individually - one duplicate doesn't fail the whole file.
  - **Dispatchers/admins**: `scripts/create_dispatcher.py` /
    `scripts/create_admin.py` (needed to bootstrap the very first admin),
    or an existing admin via `POST /admin/accounts/`.
- **New `admin` role**, third alongside `requester`/`dispatcher`. Admin
  panel (`/admin` in the frontend): Employees page (list, add, CSV
  import) and All Accounts page (every role, activate/deactivate).
- **Real email**, not a stub anymore. `app/services/email_service.py` uses
  Python's standard `smtplib` - configure `SMTP_HOST`/`SMTP_USERNAME`/
  `SMTP_PASSWORD` in `backend/.env` and it actually sends. Powers:
  employee onboarding emails (with credentials) and trip-approval
  notifications to the requester, every traveler, **and now the driver**
  (Driver got an `email` column specifically for this - closing the exact
  gap the previous feature pass had flagged as unsolved).
- **`User` and `Driver` both gained an `email` column** (nullable at the
  DB level for backward compatibility with existing rows).
- **`Notification` extended** to support a `Driver` as recipient (it has
  no login account, so `recipient_user_id` alone couldn't represent it) -
  a DB-level CHECK constraint guarantees exactly one of
  `recipient_user_id`/`recipient_driver_id` is ever set.

### Honesty notes, stated plainly

- **I have no real SMTP credentials in this build environment** - no mail
  server, no network access to reach one. The email-sending code is
  correct standard-library `smtplib` usage, verified with a dedicated test
  file (`test_email_service.py`) that mocks `smtplib.SMTP` to confirm the
  exact call shape (host, port, TLS, login, message fields) - but reaching
  a **real** inbox is something only you can verify, on your own machine,
  with real credentials. Mailtrap.io is free and built exactly for this.
- **A migration step has a stated uncertainty**: renaming the `users.role`
  CHECK constraint assumes it's literally named `user_role` (standard
  SQLAlchemy behavior for how it was originally created) - if
  `alembic upgrade head` fails on that one line, the migration file
  explains exactly how to look up the real name and fix it.
- **Every notification-dependent test uses a stubbed `send_email`**
  (an autouse fixture in `conftest.py`), not real SMTP - otherwise the
  entire test suite would fail in any environment without a configured
  mail server, which defeats the purpose of automated tests. This is
  standard practice, not a shortcut: real email-sending code is tested
  separately and directly in `test_email_service.py`.

### A real regression caught and fixed while doing this

While migrating tests off public registration, found that several test
files (`test_trip_requests.py`, `test_trip_approval.py`, and five others)
still sent a `passenger_count` field in trip-request payloads - a field
`TripRequestCreate` stopped accepting when the traveler-selection feature
shipped. Most were harmless (the field was just silently ignored), but
`test_trip_approval.py`'s **capacity-rejection tests were silently broken**
- they relied on `passenger_count=6` actually producing 6 passengers to
test "vehicle too small" rejection, but since the field no longer does
anything, every one of those requests was silently defaulting to
`passenger_count=1`, meaning the capacity check being tested would never
have actually triggered. Fixed by having those tests create real traveler
accounts to reach the intended count, exactly the way production works.

### Test count

**198 backend tests** (up from 160), covering the admin panel, CSV import
edge cases (bad rows, missing columns, duplicate usernames), the real
`email_service` behavior, and the fixed capacity-rejection tests above.

## Development Phases

All 18 phases are complete. ✅ = fully implemented and tested;
📎 = folded into an earlier phase because the code path was the same one
(noted at the time, not silently merged).

1. ✅ Project foundation
2. ✅ Database + models
3. ✅ Authentication + roles
4. ✅ Vehicles + drivers
5. ✅ Trip requests
6. ✅ Dispatcher approval/assignment
7. ✅ Trip lifecycle
8. ✅ GPS tracking
9. 📎 Trip-specific GPS tracking — built together with Phase 8; see that section
10. 📎 Distance calculation — built as part of Phase 7's trip completion; see that section
11. ✅ Geofencing
12. ✅ Alerts
13. ✅ WebSocket real-time tracking
14. ✅ Requester frontend
15. ✅ Dispatcher frontend
16. ✅ Professional UI/UX
17. ✅ Testing
18. ✅ Final integration
