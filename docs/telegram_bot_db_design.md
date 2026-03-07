# Telegram Bot — Database Design

## Overview

Four new tables are added to support the Telegram bot. No existing tables are modified.

```
telegram_users
    ├── telegram_otp          (OTP verification for registration)
    └── notification_subscriptions
            └── notification_log
```

---

## Tables

### `telegram_users`

Stores every user who has interacted with the bot. A user is considered registered only once OTP verification succeeds (`is_active = true`).

| Column | Type | Notes |
|---|---|---|
| `chat_id` | BIGINT | PK — Telegram's unique user identifier |
| `username` | VARCHAR | Telegram @username, nullable |
| `first_name` | VARCHAR | |
| `is_active` | BOOLEAN | `false` on creation, set to `true` after OTP verified |
| `created_at` | TIMESTAMP | |

---

### `telegram_otp`

Stores OTP codes issued during registration. Kept as a separate table so multiple attempts (e.g. resend) are each tracked as their own row.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL | PK |
| `chat_id` | BIGINT | FK → `telegram_users` |
| `otp_code` | VARCHAR | Generated code sent to the user |
| `created_at` | TIMESTAMP | When the OTP was issued |
| `expires_at` | TIMESTAMP | Typically `created_at + 5 minutes` |
| `verified_at` | TIMESTAMP | Null until user submits the correct code |
| `is_used` | BOOLEAN | Prevents reuse of a valid but already-consumed code |

---

### `notification_subscriptions`

Each row represents a persistent, recurring subscription: notify this user when any bus of `route_id` is approaching `stop_id`. A user may have many subscriptions.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL | PK |
| `chat_id` | BIGINT | FK → `telegram_users` |
| `stop_id` | VARCHAR | No DB-level FK — see GTFS Reload note below |
| `route_id` | VARCHAR | No DB-level FK — see GTFS Reload note below |
| `notify_minutes_before` | INTEGER | Alert threshold in minutes, e.g. `5` |
| `is_active` | BOOLEAN | User can pause without deleting the subscription |
| `created_at` | TIMESTAMP | |

---

### `notification_log`

Deduplication guard. One row is written per subscription per trip per service date, ensuring exactly one Telegram message is sent regardless of how many GTFS-RT polling cycles see the same trip approaching.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL | PK |
| `subscription_id` | INTEGER | FK → `notification_subscriptions` |
| `trip_id` | VARCHAR | No DB-level FK — see GTFS Reload note below |
| `service_date` | DATE | Calendar date of the trip run (not a timestamp) |
| `sent_at` | TIMESTAMP | Actual time the message was dispatched |
| `status` | VARCHAR | `sent` or `failed` |

**Unique constraint:** `(subscription_id, trip_id, service_date)`
Enforces at the database level that a subscription fires at most once per trip per day.

---

## Registration Flow

```
User sends /start
    → INSERT into telegram_users (is_active = false)
    → Generate OTP code
    → INSERT into telegram_otp (expires_at = now + 5min, is_used = false)
    → Send OTP code via Telegram

User replies with code
    → SELECT latest telegram_otp WHERE chat_id = ? ORDER BY created_at DESC
    → Validate: is_used = false AND expires_at > now AND otp_code matches
    → If valid:
          UPDATE telegram_otp SET is_used = true, verified_at = now
          UPDATE telegram_users SET is_active = true
    → If invalid/expired:
          Reject — user must request a new code (/start again)
```

---

## Notification Flow (per GTFS-RT poll, every 8 seconds)

```
For each active subscription:
    → Query stop_times for trips of route_id arriving at stop_id
       within notify_minutes_before minutes
    → For each matching trip:
          Check notification_log for (subscription_id, trip_id, service_date)
          → Already exists: skip (deduped)
          → Does not exist:
                Send Telegram message to chat_id
                INSERT into notification_log (status = sent/failed)

Next bus of same route → different trip_id → new log entry → notifies again
Same bus, same day    → same trip_id + service_date → already logged → skipped
Same bus, next day    → new service_date → notifies again
```

---

## Notes

### GTFS Reload Compatibility

`GTFSDataReloader` runs at 03:00 AM and **drops then recreates all GTFS tables** (`routes`, `trips`, `stops`, `stop_times`). To avoid breaking the bot tables:

- `stop_id` and `route_id` in `notification_subscriptions` use **no DB-level FK constraint** to GTFS tables. Existence is validated in application logic at subscription creation time only.
- `trip_id` in `notification_log` likewise carries **no DB-level FK**. After a reload, old trip IDs are invalid but the rows are harmless — they will never match new trips.
- `notification_log` should be **purged as part of `DatabaseReset.run_all()`** since all trip IDs are regenerated on each reload. Stale log entries would not cause bugs but accumulate unnecessarily.

### Other Notes

- `trip_id` in `notification_log` may originate from either `trips` (scheduled) or `added_trips` (GTFS-RT ADDED trips). No strict FK is needed — store the raw ID string.
- OTP expiry is enforced in application logic; old unverified rows in `telegram_otp` can be purged periodically.
- Subscriptions with `is_active = false` are ignored by the notification worker but preserved so the user can reactivate without re-subscribing.
