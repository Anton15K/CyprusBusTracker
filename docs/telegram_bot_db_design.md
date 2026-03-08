# Telegram Bot — Database Design

## Overview

Five new tables are added to support the Telegram bot. No existing tables are modified.

```
telegram_users
    ├── telegram_otp          (OTP verification for registration)
    ├── pending_web_sessions  (short-lived tokens for browser↔Telegram linking)
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

### `pending_web_sessions`

Stores short-lived tokens used to link a browser session to a Telegram account. The browser generates a subscription request; the user proves ownership of their Telegram account by forwarding the token to the bot; the bot claims it; the backend issues a JWT.

| Column | Type | Notes |
|---|---|---|
| `token` | VARCHAR | PK — cryptographically random string shown to the user |
| `chat_id` | BIGINT | FK → `telegram_users`, NULL until the bot claims the token |
| `created_at` | TIMESTAMP | |
| `expires_at` | TIMESTAMP | e.g. `created_at + 10 minutes` |

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

## Web Linking Flow (Browser → Telegram → JWT)

The browser has no intrinsic knowledge of a visitor's Telegram identity. Storing a raw `@username` or `chat_id` in a cookie would be insecure — anyone could spoof it. Instead, the Telegram bot acts as the **verification authority**: a session is only trusted after the user proves they own the Telegram account by interacting with the bot.

```
1. User clicks "Subscribe to notifications" in the web app
        → POST /api/auth/link-request
        → Backend generates a cryptographically random token (e.g. "A3F9X2")
        → INSERT into pending_web_sessions (token, chat_id=NULL, expires_at=now+10min)
        → Returns token to browser

2. Web app shows: "Send /link A3F9X2 to @CyprusBusBot on Telegram"
        → Browser polls GET /api/auth/link-status?token=A3F9X2 every 2 seconds

3. User sends "/link A3F9X2" in Telegram
        → Bot looks up token in pending_web_sessions
        → Validates: chat_id IS NULL AND expires_at > now
        → UPDATE pending_web_sessions SET chat_id = <user's chat_id> WHERE token = ?
        → Bot replies: "Linked! You can now manage subscriptions on the web."

4. Browser poll receives chat_id from /api/auth/link-status
        → Backend signs a JWT: { "chat_id": 123456789, "exp": now+30days }
        → Returns JWT to browser; browser stores it as an httpOnly cookie

5. All subsequent subscription API calls include the JWT cookie
        → Backend verifies signature + expiry, extracts chat_id
        → Uses chat_id to INSERT / UPDATE notification_subscriptions
```

### JWT Details

- **Algorithm:** HS256 (shared secret in `Settings`)
- **Payload:** `{ "chat_id": <int>, "exp": <unix timestamp> }`
- **Storage:** `httpOnly`, `Secure`, `SameSite=Strict` cookie — never exposed to JavaScript
- **No server-side session table needed** — the JWT is self-contained; `chat_id` is extracted on every request by verifying the signature
- **Expiry:** 30 days; user must re-link if expired

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
