-- Runs once, on first container start, via the postgis image's
-- docker-entrypoint-initdb.d mechanism. Creates a separate database for
-- the test suite so `pytest` never touches development data.
CREATE DATABASE fms_test_db;
\connect fms_test_db
CREATE EXTENSION IF NOT EXISTS postgis;
