# CyprusBusTracker - Cyprus Bus Tracking Application

> A modern, user-focused bus tracking application for Cyprus with real-time notifications and an enhanced UI/UX experience.

---

## Project Overview

CyprusBusTracker provides a superior bus tracking experience for Cyprus. It leverages official GTFS and GTFS-Realtime data to show live bus positions, predicted arrival times, and interactive trip planning.

**Key Differentiation:** A proactive notification system via Telegram that alerts you when your bus is approaching your stop, so you never miss a ride.

---

## Architecture & Tech Stack

- **Frontend:** Server-rendered HTML using Jinja2 templates and Leaflet.js for interactive maps.
- **Backend:** FastAPI (Python) handling API requests, frontend rendering, and GTFS processing.
- **Telegram Bot:** Separate Docker service for Telegram polling and notification delivery.
- **Database:** PostgreSQL (with `asyncpg` and SQLAlchemy `asyncio`) for static transit data.
- **Routing Engine:** OpenTripPlanner (OTP) for trip planning and point-to-point routing.
- **Notifications:** Telegram Bot API for real-time alerts.
- **Scheduling:** APScheduler for background tasks (GTFS reloads, notification checks).

---

## Core Features

- **Live Map:** Real-time bus positions with route visualization.
- **Stop Details:** View upcoming arrivals at any stop for the next 60 minutes.
- **Telegram Notifications:**
    - Link your Telegram account directly from the web map.
    - Subscribe to specific routes at specific stops.
    - Get notified ~10 minutes before the bus arrives.
- **Trip Planner:** Find the best route between any two points in Cyprus.
- **Automatic Data Updates:** Daily GTFS data reloads to keep schedules accurate.

---

## Getting Started

The project uses `uv` for Python dependency management. All commands should be executed from the **project root**.

### Local Development Setup

1.  **Install dependencies:**
    ```bash
    uv sync --frozen --group dev
    ```
2.  **Environment Variables:**
    Copy `backend/.env.example` to `backend/.env` and adjust settings.
    - Requires a running PostgreSQL instance (default: `localhost:5432`).
    - Add your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_BOT_NAME` for notification features.
3.  **Run the application:**
    ```bash
    uv run python -m backend.app.main
    ```
    *Note: On startup, the app downloads GTFS data, builds the OTP graph (requires Java + `otp-shaded-2.7.0.jar`), and populates the database. Set `MANAGE_OTP=false` in your `.env` to skip OTP graph build if it's already done.*

### Full Stack via Docker

To run the entire stack (PostgreSQL, FastAPI backend, Telegram bot, OpenTripPlanner) using Docker:

```bash
docker compose up
```

The Telegram bot runs as a separate `telegram-bot` service. It uses the same PostgreSQL database as the backend, but its logs can be viewed separately:

```bash
docker compose logs -f backend
docker compose logs -f telegram-bot
docker compose logs -f db
```

---

## Development Commands

All commands must be run from the **project root**.

### Linting and Formatting

We use `ruff` to maintain code quality.

```bash
# Check for linting issues
uv run ruff check backend/app/ backend/tests/ backend/bot/

# Check formatting
uv run ruff format --check backend/app/ backend/tests/ backend/bot/

# Auto-fix issues and format
uv run ruff check --fix backend/app/ backend/tests/ backend/bot/
uv run ruff format backend/app/ backend/tests/ backend/bot/
```

### Testing

We use `pytest` with asynchronous support and mocked dependencies.

```bash
# Run all tests
uv run pytest backend/tests/ -v

# Run specific test modules
uv run pytest backend/tests/test_api/test_buses.py -v
uv run pytest backend/tests/test_bot/ -v
```

### Telegram Bot Commands

Once your account is linked via the web UI, you can use these commands in Telegram:
- `/start`: Get your link code.
- `/subscribe <stop_id> <route_id>`: Subscribe to arrival notifications.
- `/subscriptions`: List your active subscriptions.
- `/unsubscribe <subscription_id>`: Remove a subscription.

---

## License

This project is licensed under the MIT License. Transit data is sourced from the [Cyprus National Open Data Portal](https://www.data.gov.cy) and is subject to their terms.
