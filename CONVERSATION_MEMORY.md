# Project Memory & Handoff State

## Context
This project is **FlexURL**, a URL shortener built with FastAPI, SQLModel/PostgreSQL, Redis, and a Vanilla JS frontend.
We are implementing premium subscription features (passwords, custom fallback URLs, iOS/Android target routing, real-time webhooks, bot detection, city-level geolocation analytics, and CSV log exports).

---

## Current Development State

### 1. Backend (Fully Implemented & Secured)
All backend logic supporting premium capabilities and security validation is active:
- **`backend/models.py`:** Removed the `unique=True` constraint from the `long_url` column in `urldata` table. This allows users to create custom aliases/premium target configurations for a destination even if it was previously shortened.
- **`backend/database.py`:**
  - In `init_db()`, added automatic SQL code execution to safely drop the PostgreSQL index/constraint `urldata_long_url_key` if it exists.
  - Updated `is_long_url_exists` to partition URL lookups by ownership, checking if the current user has already shortened the URL. If the user is logged in, it also checks for and adopts anonymous links, preventing returning other users' short codes.
- **`backend/short_url_gen.py`:** Removed `is_long_url_exists` check in `add_custom_url` to allow the creation of custom URL shortcuts for any destination.
- **`backend/app.py`:**
  - **Route Ordering Fix:** Moved the `@app.post("/shorten")` route above the wildcard `@app.post("/{short_url}")` route. This resolves a routing conflict where wildcard parameter routing captured POST requests to `/shorten` and threw a `404 Short URL not found` error.
  - **Dynamic Redis check:** Premium links are marked in Redis as `"DYNAMIC"` (instead of standard redirects) to enforce SQL database checks on access.
  - **Redirect handling:** Gate serving for password-protected links, smart routing based on request User-Agent (`iOS` or `Android`), firing post-redirect webhooks asynchronously, and custom expired URL redirects.
  - **Export:** Premium-only endpoint `GET /api/analytics/{short_url}/export` to stream raw click logs as CSV.
  - **Admin Tier Toggle:** Secured `POST /api/user/toggle-tier` to only allow the developer email specified in `ADMIN_EMAIL` env variable.
  - **Anonymous Link Rate Limiter:** Capped anonymous URL creations to 5 links per 24 hours per IP address using Redis to prevent database spamming.
  - **Resource Exhaustion Bounds:** Constrained the `limit` query parameter on `GET /api/user/recent-clicks` to prevent DoS.
  - **SSRF Validation:** Enforced private network validations on all premium parameter URLs (`webhook_url`, `ios_url`, `android_url`, `fallback_url`) using `is_valid_url`.
  - **Recent Click Stream Payload:** Updated `GET /api/analytics/{short_url}` and pre-rendered HTML template payload to query and return the 5 most recent visitor click log entries if the owner has premium.
  - **Proactive Alias Validation:** Added verification in `/shorten` to return a `400 Bad Request` if a custom alias is already taken.
  - **Session User ID Type Casting:** Cast decoded JWT `user_id` values to `int` inside `/shorten`, `/api/analytics/{short_url}`, `/api/analytics/{short_url}/export`, `/analytics/{short_url}`, `/api/user/recent-clicks`, `/api/user/links`, `/api/user/account`, and `/api/user/delete-custom-url` routes to eliminate type mismatch issues against database integer values.
  - **Anonymous Analytics Access:** Enabled Premium users to view analytics for anonymous links (`user_id is None`) by adjusting the ownership validation checks.

### 2. Frontend UI
All frontend interface files are completed with high-impact, premium aesthetics:
- **[index.html](file:///D:/urlshortener/frontend/index.html):** Added a Premium Advanced Settings panel (Webhook URL, Passcode Protection, iOS Target, Android Target, Fallback URL) that is automatically revealed under the shorten widget for premium subscribers. Submits parameters in the POST body to `/shorten`.
- **[dashboard.html](file:///D:/urlshortener/frontend/dashboard.html):** Removed the "Delete My Account" button from the Profile settings section. Added a modern gradient welcome hero card for premium users and locked analytics button with a ban symbol modal warning for free users.
- **[analytics.html](file:///D:/urlshortener/frontend/analytics.html):** Recreated as a stunning, dark-themed command-center style dashboard featuring:
  - *Dynamic Bot Traffic Filter Switch:* A toggle that instantly filters out crawler/bot clicks from all charts and totals with smooth layout recalculations.
  - *Real-time click feed:* A live visual list of the last 5 visitors showing IP addresses, geolocated cities, device details, and human/bot badge categorization.
  - *Custom Chart styles:* Hand-crafted Chart.js configurations with customized tooltips, layout alignments, border radii, and glowing linear fills.
  - *Data Pre-Rendering:* Supports `window.__INITIAL_DATA__` injection to eliminate background API requests on load.
  - *TypeError Crash Fixes:* Restored the missing DOM element `display-created-at` in the Destination layout row, and added defensive check conditions to ensure updates to `metric-device` bypass errors if its card is absent, preventing the page layout from crashing and displaying the "Access Denied" error state card.
  - *Chart Render Optimization:* Disabled Chart.js entry animations (`animation: false` on line, bar, and doughnut charts) to completely eliminate browser layout rendering lag when drawing multiple chart canvases concurrently or toggling bot traffic filters.

---

## Database & Caching Status
- Constraint `urldata_long_url_key` has been dropped, allowing duplicates.
- Caching logic handles `"Expired"`, `"DYNAMIC"`, and standard direct caching seamlessly.
- Maintained `ndgaming458@gmail.com` as `"premium"` tier, and successfully reverted `nirbhayerror@gmail.com` back to `"free"` tier in the database.

---

## Active Rules
- **No emojis** in code, templates, or documentation.
- **Never touch the backend folder** when creating/modifying frontend UI files unless explicitly instructed.
- All database inputs must use **timezone-naive UTC datetimes**.

---

## Next Steps for Future Sessions
If a new conversation is started, the next step is to test the integration in production or add new payment gateway hooks.
