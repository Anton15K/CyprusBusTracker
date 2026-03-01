# CyprusBusTracker - Cyprus Bus Tracking Application

> A modern, user-focused bus tracking application for Cyprus with real-time notifications and an enhanced UI/UX experience.

---

## Project Overview

### The Idea

CyprusBusTracker is a fork and enhancement of [busonmap.com](https://busonmap.com) / [cyprusbus.info](https://cyprusbus.info), a real-time bus tracking application for Cyprus. While the existing solutions provide basic bus tracking functionality, they lack modern UI patterns and proactive notification features that today's commuters expect.

**Our goal:** Create a superior bus tracking experience that not only shows where buses are, but actively helps users catch their bus by notifying them when their chosen bus arrives at their chosen stop and informing them about the next bus.

### Problem Statement

Current Cyprus bus tracking apps have several limitations:

1. **Basic UI** - Map-centric interfaces that require constant monitoring
2. **Passive Experience** - Users must actively check the app; no proactive alerts
3. **Limited Trip Planning** - No "notify me when bus X reaches stop Y" functionality
4. **Poor Mobile Experience** - Not optimized for on-the-go usage

### Solution

CyprusBusTracker addresses these issues by:

- Implementing a modern, mobile-first UI with intuitive navigation
- Adding push notifications for bus arrivals at user-selected stops
- Providing ETA predictions and "next bus" information
- Offering a cleaner, more accessible interface

---

## Data Source

The application will leverage Cyprus's official open data:

- **Provider:** [Cyprus National Open Data Portal](https://www.data.gov.cy) / [traffic4cyprus.org.cy](https://traffic4cyprus.org.cy)
- **Format:** GTFS (General Transit Feed Specification) & GTFS-Realtime
- **License:** Creative Commons Attribution 4.0
- **Data includes:**
  - Static: Routes, stops, schedules, frequencies
  - Real-time: Vehicle positions, trip updates, service alerts

---

## Core Features

### 1. Real-Time Bus Tracking (Enhanced)

| Feature | Description |
|---------|-------------|
| Live Map | Interactive map showing all active buses |
| Bus Details | Route number, direction, speed, occupancy (if available) |
| Route Visualization | Click a bus to see its full route on the map |
| Stop Markers | All bus stops displayed with tap-to-view details |
| Auto-Refresh | Positions update every 10 seconds |

### 2. Smart Notifications (New)

**The key differentiator of CyprusBusTracker.**

| Notification Type | Description |
|-------------------|-------------|
| **Bus Arrival Alert** | "Bus 101 has arrived at Makariou Avenue stop" |
| **Approaching Alert** | "Bus 101 is 2 stops away (~3 min)" |
| **Next Bus Info** | "Next bus 101 in 12 minutes" |
| **Service Alerts** | Delays, cancellations, route changes ? |
| **Custom Reminders** | Set recurring alerts for daily commute |

**Notification Flow:**
```
User selects:  Stop → Route → Alert Type → Time Window
                 ↓
System monitors: Real-time bus positions
                 ↓
Trigger:        When conditions met → Push notification
```

### 3. Stop-Centric View (New)

Instead of only map view, offer a stop-focused interface:

- Search for any stop by name or number
- View all routes serving that stop
- See real-time arrivals for all buses at that stop
- One-tap "Notify me" for any arriving bus

### 4. Trip Planner

- Point A to Point B routing
- Multi-leg journey support
- Real-time adjustments based on delays
- Walking directions to nearest stop

---

## UI/UX Improvements

### Design Principles

1. **Mobile-First** - Designed for one-handed use
2. **Glanceable** - Key info visible at a glance
3. **Offline-Capable** - Basic functionality without connection




### UI Improvements Over Existing Apps

| Current Issue | CyprusBusTracker Solution |
|---------------|-------------------|
| Map dominates entire screen | Hybrid view with cards + mini-map |
| Hard to find specific stops | Prominent search with autocomplete |
| Dense information on bus popups | Clean, hierarchical info display |
| Small touch targets | Large, thumb-friendly buttons |
| Hard to navigate map | Better map with view from sputnics |

---

## Use Cases

### Use Case 1: Daily Commuter

**Persona:** Maria, 32, works in Nicosia, takes bus 101 daily

**Scenario:**
1. Maria opens app while having morning coffee
2. She sees her saved "Home Stop" showing "Bus 101 in 8 min"
3. She taps "Alert me when 2 stops away"
4. Gets push notification: "Bus 101 approaching - leave now!"
5. Walks to stop, bus arrives 1 minute later

**Value:** Never misses the bus, no need to constantly check app

### Use Case 2: Tourist/Occasional User

**Persona:** John, 45, visiting Limassol for a week

**Scenario:**
1. John wants to go from hotel to the beach
2. Opens app, taps "Near Me" to find closest stop
3. Sees which buses serve that stop and their destinations
4. Taps on a bus to see its full route on map
5. Sets alert for when bus is approaching
6. Explores the city with confidence

**Value:** Easy discovery of public transport without local knowledge

### Use Case 3: Waiting at Stop

**Persona:** Elena, 19, student waiting at a busy interchange

**Scenario:**
1. Elena is at a stop served by 6 different routes
2. Opens app, it auto-detects her location
3. Sees real-time arrivals for ALL buses at her stop
4. Notices her usual bus is delayed
5. Quickly sees an alternative route arriving sooner
6. Takes the alternative, saves 10 minutes

**Value:** Real-time decisions based on actual conditions

---

## Technical Specification

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│  ┌──────────────────────────────────────┐               │
│  │  Jinja2 Templates + Leaflet.js       │               │
│  └──────────────────────────────────────┘               │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Backend                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Python    │  │   Redis     │  │  PostgreSQL │      │
│  │   FastAPI   │  │   Cache     │  │             │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐                       │
│  │   GTFS-RT   │  │   Telegram  │                       │
│  │   Processor │  │   bot       │                       │
│  └─────────────┘  └─────────────┘                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   External APIs                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │     Cyprus GTFS / GTFS-RT Open Data Feed        │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Jinja2 + Leaflet.js | Server-rendered, no build step |
| **Backend** | Python + FastAPI | Fast, async, great for real-time |
| **Database** | PostgreSQL | Lat/lon stored as floats |
| **Cache** | Redis | GTFS-RT response caching under load |
| **Push Notifications** | Telegram Bot API | Widely used, no app install required |

### API Endpoints

```
# Implemented
GET  /api/get_buses                        # All active buses (real-time)
GET  /buses/get_stops_on_route/{route_id}  # Stops on a route
GET  /api/get_shape/{route_id}             # Route geometry
GET  /stops/{stop_id}                      # Arrivals at a stop (next hour)
GET  /stops/routes_stopping_at/{stop_id}   # Routes serving a stop
POST /api/make_route                       # Trip plan A → B via OTP

# Planned (notifications)
POST /api/alerts                           # Create alert (stop + route)
GET  /api/alerts                           # List active alerts
DEL  /api/alerts/:id                       # Delete alert
```

### Notification System Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   User       │     │   Alert      │     │   GTFS-RT    │
│   Creates    │────▶│   Service    │◀────│   Processor  │
│   Alert      │     │              │     │   (10s poll) │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Condition  │
                     │   Evaluator  │
                     └──────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ "Bus at  │ │"Bus 2    │ │"Next bus │
        │  stop"   │ │ stops    │ │ in X min"│
        │          │ │ away"    │ │          │
        └──────────┘ └──────────┘ └──────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Telegram   │
                     │   Bot        │
                     └──────────────┘
```

---

## Development Phases

### Phase 1: MVP (4-6 weeks)

**Goal:** Working app with core tracking and basic notifications

- [x] Project setup and CI/CD
- [x] GTFS/GTFS-RT data ingestion
- [x] Basic map view with live buses
- [x] Stop search and details
- [ ] Simple "notify when bus arrives" feature (Telegram)
- [ ] PWA manifest for mobile

**Deliverable:** Usable web app with real-time tracking

### Phase 2: Enhanced Features (4-6 weeks)

**Goal:** Full notification system and personalization

- [ ] Advanced alerts (approaching, ETA-based)
- [x] Trip planner via OpenTripPlanner
- [ ] Service alerts integration
- [ ] Redis caching for GTFS-RT responses

**Deliverable:** Feature-complete application

---



## Development

All commands run from the `backend/` directory.

### Setup

```bash
uv sync --frozen --group dev
```

Requires PostgreSQL running at `localhost:5432`. Copy `.env.example` to `.env` and adjust as needed.

### Run locally

```bash
uv run python -m app.main
```

On startup the app downloads GTFS data, builds the OTP graph (requires Java + `otp-shaded-2.7.0.jar`), inserts into PostgreSQL, then starts serving. Set `MANAGE_OTP=false` to skip OTP graph build.

### Full stack via Docker

```bash
docker compose up   # from repo root
```

Starts PostgreSQL, the FastAPI backend, and OpenTripPlanner as separate containers.

### Lint

```bash
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/

# Auto-fix
uv run ruff check --fix app/ tests/
uv run ruff format app/ tests/
```

### Test

```bash
# All tests
uv run pytest tests/ -v

# Single file or function
uv run pytest tests/test_api/buses.py -v
uv run pytest tests/test_api/buses.py::test_get_buses -v
```

Tests mock all external dependencies (DB, GTFS-RT feed, OTP). No real services are needed to run them.

---

## License

This project specification is provided for planning purposes. The actual implementation will be open source under MIT License, respecting the Creative Commons Attribution 4.0 license of the Cyprus open data source.

---

