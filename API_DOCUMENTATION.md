# External API Documentation

This document describes the external (third-party) APIs that CyprusBusTracker consumes to obtain bus transit data for Cyprus.

---

## Table of Contents

1. [GTFS Realtime API](#1-gtfs-realtime-api)
2. [GTFS Static Data Downloads](#2-gtfs-static-data-downloads)
3. [OpenTripPlanner (OTP) GraphQL API](#3-opentripplanner-otp-graphql-api)
4. [Data Flow Overview](#4-data-flow-overview)

---

## 1. GTFS Realtime API

Provides live bus positions and trip updates using the [GTFS Realtime](https://gtfs.org/realtime/) specification.

### Endpoint

```
GET http://20.19.98.194:8328/Api/api/gtfs-realtime
```

Defined in `constants.py` as `GTFS_REALTIME_API_PATH`.

### Authentication

None required.

### Request

A simple HTTP GET with no parameters, headers, or body.

```python
import requests

response = requests.get("http://20.19.98.194:8328/Api/api/gtfs-realtime")
```

### Response

**Content-Type:** `application/x-protobuf` (binary Protocol Buffer)

The response body is a serialized [`FeedMessage`](https://gtfs.org/realtime/reference/#message-feedmessage) protobuf. It must be parsed using the GTFS Realtime protobuf schema (`gtfs_realtime_pb2`).

```python
import gtfs_realtime_pb2

feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)
```

### Data Contents

Each `FeedEntity` in `feed.entity` can contain:

#### Vehicle Positions (`entity.vehicle`)

Real-time location of a bus.

| Field | Type | Description |
|---|---|---|
| `vehicle.trip.trip_id` | string | GTFS trip identifier |
| `vehicle.trip.route_id` | string | GTFS route identifier |
| `vehicle.trip.direction_id` | int | Direction (0 or 1) |
| `vehicle.trip.start_time` | string | Scheduled start time of the trip (HH:MM:SS) |
| `vehicle.position.latitude` | float | Current latitude |
| `vehicle.position.longitude` | float | Current longitude |
| `vehicle.position.bearing` | float | Heading in degrees (optional) |
| `vehicle.position.speed` | float | Speed in m/s (optional) |

#### Trip Updates (`entity.trip_update`)

Real-time arrival/departure adjustments.

| Field | Type | Description |
|---|---|---|
| `trip_update.trip.trip_id` | string | GTFS trip identifier |
| `trip_update.trip.route_id` | string | GTFS route identifier |
| `trip_update.trip.direction_id` | int | Direction (0 or 1) |
| `trip_update.trip.schedule_relationship` | enum | `SCHEDULED`, `ADDED`, or `CANCELED` |
| `trip_update.trip.start_time` | string | Scheduled start time |
| `trip_update.stop_time_update[]` | array | Per-stop arrival/departure updates |

Each `stop_time_update` contains:

| Field | Type | Description |
|---|---|---|
| `stop_id` | string | Stop identifier |
| `stop_sequence` | int | Order of this stop within the trip |
| `arrival.time` | int | Predicted arrival as Unix timestamp |
| `departure.time` | int | Predicted departure as Unix timestamp |

### Schedule Relationships

- **SCHEDULED** — Normal trip with a known `trip_id`. Stop times are updates to the static schedule.
- **ADDED** — Unscheduled trip not present in the static GTFS. Has no `trip_id`; identified by `route_id` + `direction_id` + `start_time`. The application dynamically creates trip IDs for these.
- **CANCELED** — Trip has been canceled and should be ignored.

### Polling Frequency

The frontend polls `GET /api/get_buses` every **8 seconds**, which internally fetches from this API.

---

## 2. GTFS Static Data Downloads

Static schedule data (routes, stops, trips, stop times, shapes) in standard [GTFS](https://gtfs.org/schedule/) format, provided by [Motion Bus Card Cyprus](https://www.motionbuscard.org.cy/).

### Base URL

```
https://www.motionbuscard.org.cy/opendata/downloadfile
```

### Authentication

None required.

### Endpoints

Each URL downloads a ZIP file for a specific bus operator/agency:

| Feed ID | URL |
|---|---|
| 6 | `https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C6_google_transit.zip&rel=True` |
| 2 | `https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C2_google_transit.zip&rel=True` |
| 4 | `https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C4_google_transit.zip&rel=True` |
| 5 | `https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C5_google_transit.zip&rel=True` |
| 9 | `https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C9_google_transit.zip&rel=True` |
| 10 | `https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C10_google_transit.zip&rel=True` |
| 11 | `https://www.motionbuscard.org.cy/opendata/downloadfile?file=GTFS%5C11_google_transit.zip&rel=True` |

All URLs are defined in `constants.py` as `ZIP_URLS`.

### Query Parameters

| Parameter | Value | Description |
|---|---|---|
| `file` | `GTFS\{id}_google_transit.zip` | Path to the GTFS zip on the server (`%5C` = `\`) |
| `rel` | `True` | Indicates relative path resolution |

### Response

**Content-Type:** `application/zip`

Each ZIP archive contains standard GTFS CSV files. The application uses the following files (defined in `constants.py` as `ALLOWED_FILES`):

| File | Description |
|---|---|
| `agency.txt` | Transit agencies |
| `routes.txt` | Bus routes (route_id, short name, long name) |
| `trips.txt` | Individual trips (trip_id, route_id, service_id, direction_id, headsign) |
| `stops.txt` | Bus stops (stop_id, name, latitude, longitude, zone_id) |
| `stop_times.txt` | Scheduled arrival/departure at each stop for each trip |
| `calendar_dates.txt` | Service dates — maps `service_id` to specific dates |
| `shapes.txt` | Route geometry points (shape_id, lat, lon, sequence) |

### GTFS File Schemas

#### routes.txt

| Column | Type | Description |
|---|---|---|
| `route_id` | int | Unique route identifier |
| `route_short_name` | string | Short display name (e.g. "101") |
| `route_long_name` | string | Full route name (e.g. "Nicosia - Larnaca") |

#### trips.txt

| Column | Type | Description |
|---|---|---|
| `trip_id` | int | Unique trip identifier |
| `route_id` | int | References `routes.route_id` |
| `service_id` | int | Service calendar identifier |
| `direction_id` | int | Direction of travel (0 or 1) |
| `trip_headsign` | string | Destination display text |

#### stops.txt

| Column | Type | Description |
|---|---|---|
| `stop_id` | int | Unique stop identifier |
| `stop_name` | string | Name of the stop |
| `stop_lat` | float | Latitude |
| `stop_lon` | float | Longitude |
| `zone_id` | int | Fare zone |

#### stop_times.txt

| Column | Type | Description |
|---|---|---|
| `trip_id` | int | References `trips.trip_id` |
| `arrival_time` | string | Arrival time in `HH:MM:SS` format (can exceed 24:00:00) |
| `departure_time` | string | Departure time in `HH:MM:SS` format |
| `stop_id` | int | References `stops.stop_id` |
| `stop_sequence` | int | Order of this stop within the trip |

#### shapes.txt

| Column | Type | Description |
|---|---|---|
| `shape_id` | int | Matches `route_id` in this application |
| `shape_pt_lat` | float | Latitude of shape point |
| `shape_pt_lon` | float | Longitude of shape point |
| `shape_pt_sequence` | int | Order of shape points |

#### calendar_dates.txt

| Column | Type | Description |
|---|---|---|
| `service_id` | int | Service identifier |
| `date` | string | Date in `YYYYMMDD` format |
| `exception_type` | int | 1 = service added, 2 = service removed |

### Refresh Schedule

Static GTFS data is downloaded and reprocessed **daily at 03:00 AM** (Asia/Nicosia timezone). Multiple agency feeds are merged into a single GTFS bundle for OpenTripPlanner.

---

## 3. OpenTripPlanner (OTP) GraphQL API

[OpenTripPlanner](https://www.opentripplanner.org/) is run as a local service for multi-modal trip planning. It is **not an external API** — it runs locally, built from the downloaded GTFS + OSM data. Documented here because it is a key dependency.

### Endpoint

```
POST http://localhost:8080/otp/gtfs/v1
```

### Headers

```
Content-Type: application/json
```

### Request Body

GraphQL query with trip planning parameters. The full query template is in `constants.py` as `GRAPHQL_QUERY`.

```json
{
  "query": "query GtfsExampleQuery { planConnection(...) { ... } }"
}
```

#### Query Parameters (interpolated into the query string)

| Parameter | Type | Description |
|---|---|---|
| `lat_from` | float | Origin latitude |
| `lon_from` | float | Origin longitude |
| `lat_to` | float | Destination latitude |
| `lon_to` | float | Destination longitude |
| `time_value` | string | Earliest departure in ISO 8601 format (e.g. `2026-02-14T10:30+02:00`) |

#### GraphQL Query

```graphql
query GtfsExampleQuery {
  planConnection(
    origin: {
      location: { coordinate: { latitude: $lat_from, longitude: $lon_from } }
    }
    destination: {
      location: { coordinate: { latitude: $lat_to, longitude: $lon_to } }
    }
    dateTime: { earliestDeparture: "$time_value" }
    modes: {
      direct: [WALK]
      transit: { transit: [{ mode: BUS }, { mode: RAIL }] }
    }
  ) {
    edges {
      node {
        start
        end
        legs {
          mode
          from { name, lat, lon, departure { scheduledTime, estimated { time, delay } } }
          to { name, lat, lon, arrival { scheduledTime, estimated { time, delay } } }
          route { gtfsId, longName, shortName }
          legGeometry { points }
        }
      }
    }
  }
}
```

### Response

```json
{
  "data": {
    "planConnection": {
      "edges": [
        {
          "node": {
            "start": "2026-02-14T10:35:00+02:00",
            "end": "2026-02-14T11:20:00+02:00",
            "legs": [
              {
                "mode": "WALK",
                "from": {
                  "name": "Origin",
                  "lat": 35.1856,
                  "lon": 33.3823,
                  "departure": {
                    "scheduledTime": "2026-02-14T10:35:00+02:00",
                    "estimated": { "time": "...", "delay": 0 }
                  }
                },
                "to": {
                  "name": "Bus Stop A",
                  "lat": 35.1860,
                  "lon": 33.3830,
                  "arrival": { "scheduledTime": "..." }
                },
                "route": null,
                "legGeometry": { "points": "encoded_polyline_string" }
              },
              {
                "mode": "BUS",
                "from": { "name": "Bus Stop A", "lat": 35.186, "lon": 33.383 },
                "to": { "name": "Bus Stop B", "lat": 35.174, "lon": 33.362 },
                "route": {
                  "gtfsId": "1:101",
                  "longName": "Nicosia - Larnaca",
                  "shortName": "101"
                },
                "legGeometry": { "points": "encoded_polyline_string" }
              }
            ]
          }
        }
      ]
    }
  }
}
```

**Note:** The `legGeometry.points` field contains a [Google Encoded Polyline](https://developers.google.com/maps/documentation/utilities/polylinealgorithm). The application decodes it using the `polyline` Python library before returning it to the frontend as `[[lat, lon], ...]` arrays.

---

## 4. Data Flow Overview

```
┌──────────────────────────────────┐
│  motionbuscard.org.cy            │
│  (GTFS Static ZIP Downloads)    │
│  7 agency feeds                  │
└──────────┬───────────────────────┘
           │ Daily at 03:00 AM
           ▼
┌──────────────────────────────────┐
│  Download → Unzip → Merge CSVs  │
│  → Build OTP Graph              │
│  → Insert into PostgreSQL DB    │
└──────────┬───────────┬───────────┘
           │           │
           ▼           ▼
┌─────────────┐  ┌─────────────────┐
│ PostgreSQL  │  │ OTP Server      │
│ (schedules, │  │ (localhost:8080) │
│  stops,     │  │ trip planning    │
│  routes)    │  │ via GraphQL      │
└──────┬──────┘  └────────┬────────┘
       │                  │
       ▼                  │
┌──────────────────────────────────┐
│  20.19.98.194:8328               │
│  (GTFS-RT Protobuf Feed)        │
│  Live bus positions & trip       │
│  updates                         │
└──────────┬───────────────────────┘
           │ Every 8 seconds
           ▼
┌──────────────────────────────────┐
│  FastAPI Backend (app.py)        │
│  Merges RT data with DB         │
│  Serves internal REST API       │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│  Browser Frontend                │
│  Leaflet.js map                  │
└──────────────────────────────────┘
```

### Key Files Reference

| File | Role |
|---|---|
| `constants.py` | All API URLs, GTFS config, GraphQL query template |
| `GTFS_Parsing.py` | Parses both static GTFS CSVs and GTFS-RT protobuf feed |
| `DatabaseReset.py` | Downloads static GTFS ZIPs, merges feeds, builds OTP graph |
| `make_route.py` | Queries OTP GraphQL API for trip planning |
| `crud.py` | Database queries + orchestrates GTFS-RT fetch/update cycle |
| `app.py` | FastAPI endpoints that serve data to the frontend |
| `gtfs_realtime_pb2.py` | Auto-generated protobuf module for GTFS-RT parsing |
