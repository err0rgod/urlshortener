# Project Memory & Handoff State

## Context
This project is **FlexURL**, a URL shortener built with FastAPI, SQLModel/PostgreSQL, Redis, and a Vanilla JS frontend.
We are implementing premium subscription features (passwords, custom fallback URLs, iOS/Android target routing, real-time webhooks, bot detection, city-level geolocation analytics, and CSV log exports).

---

## Current Development State

### 1. Backend (Fully Implemented & Secured)
All backend logic supporting premium capabilities and security validation is active:
- **`backend/models.py`:** Added premium columns (`webhook_url`, `ios_url`, `android_url`, `password_hash`, `fallback_url`, `city`, `is_bot`).
- **`backend/app.py`:**
  - **Dynamic Redis check:** Premium links are marked in Redis as `"DYNAMIC"` (instead of standard redirects) to enforce SQL database checks on access.
  - **Redirect handling:** Gate serving for password-protected links, smart routing based on request User-Agent (`iOS` or `Android`), firing post-redirect webhooks asynchronously, and custom expired URL redirects.
  - **Export:** Premium-only endpoint `GET /api/analytics/{short_url}/export` to stream raw click logs as CSV.
  - **Admin Tier Toggle:** Secured `POST /api/user/toggle-tier` to only allow the developer email specified in `ADMIN_EMAIL` environment variable.
  - **Anonymous Link Rate Limiter:** Capped anonymous URL creations to 5 links per 24 hours per IP address using Redis to prevent database spamming.
  - **Resource Exhaustion Bounds:** Constrained the `limit` query parameter on `GET /api/user/recent-clicks` to prevent DoS.
  - **SSRF Validation:** Enforced private network validations on all premium parameter URLs (`webhook_url`, `ios_url`, `android_url`, `fallback_url`) using `is_valid_url`.

### 2. Frontend UI (Reverted to Commit: "Fixed social links" / `febbd21` with modifications)
Per user preference, all frontend interface files were reverted to the clean state of commit `febbd21` to keep the layout simple, with specific modifications:
- **[index.html](file:///D:/urlshortener/frontend/index.html)**
- **[dashboard.html](file:///D:/urlshortener/frontend/dashboard.html):** Modified to display a locked analytics button with a ban symbol (SVG cancel circle) for free tier users. Clicking the button pops a polite notice modal using the custom dialog template.
- **[analytics.html](file:///D:/urlshortener/frontend/analytics.html)**

---

## Database & Caching Status
- No schema migrations are outstanding. The required columns exist in the DB.
- Caching logic handles `"Expired"`, `"DYNAMIC"`, and standard direct caching seamlessly.

---

## Active Rules
- **No emojis** in code, templates, or documentation.
- **Never touch the backend folder** when creating/modifying frontend UI files unless explicitly instructed.
- All database inputs must use **timezone-naive UTC datetimes**.

---

## Next Steps for Future Sessions
If a new conversation is started, the next step is to determine how to integrate the UI controls for premium capabilities (e.g. settings panel, advanced analytics cards) onto the clean UI from `febbd21` in a way that is satisfactory.
