# CyprusBusTracker

## Project Overview

CyprusBusTracker is a modern, user-focused real-time bus tracking application for Cyprus. It aims to provide an enhanced UI/UX experience and proactive notification features compared to existing solutions.

**Architecture & Tech Stack:**
- **Frontend:** Server-rendered HTML using Jinja2 templates and Leaflet.js for interactive maps.
- **Backend:** Python application built with FastAPI. It handles API requests, serves frontend templates, and processes GTFS/GTFS-Realtime feeds.
- **Database:** PostgreSQL (with `asyncpg` and SQLAlchemy `asyncio`) for storing static GTFS data (stops, routes, schedules).
- **Routing Engine:** OpenTripPlanner (OTP) is used for trip planning and point-to-point routing.
- **Data Source:** Cyprus National Open Data Portal (GTFS and GTFS-Realtime).

## Building and Running

The project uses `uv` for Python dependency management and Docker Compose for full-stack deployment.

### Backend Setup (Local Development)
All backend commands should be run from within the `backend/` directory.

1. **Install dependencies:**
   ```bash
   cd backend
   uv sync --frozen --group dev
   ```
2. **Environment Variables:**
   Copy `.env.example` to `.env` and adjust as needed (requires a running PostgreSQL instance at `localhost:5432`).
3. **Run the application:**
   ```bash
   uv run python -m app.main
   ```
   *Note: On startup, the app downloads GTFS data, builds the OTP graph (requires Java + `otp-shaded-2.7.0.jar`), and inserts data into PostgreSQL. Set `MANAGE_OTP=false` in your `.env` to skip OTP graph build.*

### Full Stack via Docker
To run the entire stack (PostgreSQL, FastAPI backend, OpenTripPlanner) using Docker:

```bash
# Run from the project root directory
docker compose up
```

## Testing

The project uses `pytest` for testing. Tests mock all external dependencies (DB, GTFS-RT feed, OTP), so no real services need to be running.

```bash
# From the backend/ directory
# Run all tests
uv run pytest tests/ -v

# Run a specific file or test
uv run pytest tests/test_api/buses.py -v
uv run pytest tests/test_api/buses.py::test_get_buses -v
```

## Development Conventions

- **Linting and Formatting:** The project uses `ruff` to enforce coding standards. Configuration can be found in `backend/pyproject.toml` (e.g., line-length = 100).
  ```bash
  # Check for linting issues
  uv run ruff check app/ tests/
  uv run ruff format --check app/ tests/

  # Auto-fix issues and format
  uv run ruff check --fix app/ tests/
  uv run ruff format app/ tests/
  ```
- **Asynchronous Code:** The backend heavily utilizes Python's `asyncio`, leveraging asynchronous frameworks and libraries like FastAPI, asyncpg, and httpx for performance.
- **Mocking:** Unit tests strictly mock external services to ensure fast and reliable execution without relying on live databases or network feeds.
