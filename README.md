# FlexURL

FlexURL is a full-stack URL shortening platform built around FastAPI, PostgreSQL, Redis, and static Tailwind-based frontend pages. It supports anonymous and authenticated link creation, branded domains, protected redirects, analytics collection, developer API access, and subscription-aware feature gating.

This repository contains both the application backend and the static frontend served by the API process.

## Features

- Shorten long URLs into compact shareable links.
- Support custom aliases for programmatic and user-created short links.
- Resolve links through the primary host or verified custom domains.
- Enforce free-tier and anonymous creation quotas.
- Support premium link controls including:
  - password-protected links
  - activation scheduling
  - expiration handling
  - fallback URLs
  - iOS and Android specific redirect targets
  - custom countdown redirects
  - outbound webhooks on redirect events
- Run Safe Browsing checks in the background and block flagged destinations.
- Collect redirect analytics including country, city, browser, device, referer, and bot signals.
- Expose analytics views and export endpoints for managed links.
- Provide Firebase-backed authentication with JWT session cookies.
- Offer subscription-aware behavior for free, startup, business, and trial states.
- Integrate Razorpay for paid plan checkout and verification.
- Manage branded domains through Cloudflare for SaaS custom hostnames.
- Provide developer API key management and single/batch shortening endpoints.
- Accept support tickets and sales quote requests, with admin email notifications.
- Send daily operational reports and subscription dunning emails.

## Tech Stack

- Backend: FastAPI
- ORM and schema layer: SQLModel and SQLAlchemy
- Database: PostgreSQL
- Cache and queues: Redis
- Background jobs: ARQ
- Frontend: static HTML with Tailwind CSS output
- Authentication: Firebase Admin SDK plus JWT session cookies
- Payments: Razorpay
- Email delivery: Resend
- External infrastructure: Cloudflare for SaaS

## Repository Structure

```text
backend/
  app.py                 Main FastAPI application and route definitions
  auth.py                Firebase auth and session endpoints
  models.py              SQLModel tables and request schemas
  database.py            Engine setup and persistence helpers
  short_url_gen.py       Link creation and redirect resolution helpers
  arq_worker.py          Background analytics and click flush jobs
  report_scheduler.py    Daily reporting and subscription dunning
  cloudflare_saas.py     Custom hostname provisioning via Cloudflare
frontend/
  *.html                 Static pages served by FastAPI
  static/                CSS, SVG, and video assets
requirements.txt         Python dependencies
package.json             Tailwind build tooling
nginx.conf               Reverse proxy reference configuration
```

## Core Capabilities

### Link lifecycle

FlexURL stores shortened links in PostgreSQL and uses Redis for fast counters, rate limiting, and short-lived cache data. Links can be anonymous or tied to a signed-in user. Premium accounts can attach advanced redirect rules and custom domains to each link.

### Redirect and safety flow

Redirect handling supports expiration checks, activation windows, password gates, banned-link blocking, and domain-aware resolution. Newly created links are checked asynchronously against Google Safe Browsing, and flagged links are blocked from normal redirect use.

### Analytics pipeline

Redirect events are processed asynchronously through ARQ. The worker performs Geo-IP lookup, user-agent parsing, referer parsing, bot detection, click log persistence, Redis click aggregation, and optional webhook delivery for eligible accounts.

### Subscription and billing logic

The application supports free, startup, business, and trial flows. Billing is handled through Razorpay. Subscription state drives feature access, developer API eligibility, creation quotas, and grace-period behavior after plan expiration.

### Branded domains

Premium users can register custom domains. Cloudflare for SaaS is used to create and manage custom hostnames and SSL provisioning. The backend also enforces ownership and routing constraints for custom-domain links.

## Main Routes

This is not a full API reference, but these are the primary route groups implemented in the current codebase:

- Public pages: `/`, `/login`, `/dashboard`, `/documentation`, `/support`, `/quotes`, `/privacy`, `/terms`
- Authentication: `/auth/check-username`, `/auth/session`, `/auth/logout`, `/auth/me`
- Shortening and redirect: `POST /shorten`, `GET /{short_url}`, `POST /{short_url}`
- Analytics: `/api/analytics/{short_url}`, `/api/analytics/{short_url}/export`, `/analytics/{short_url}`
- User link management: `/api/user/links`, `PATCH /api/links/{short_url}`, `DELETE /api/links/{short_url}`
- Domains: `/api/domains`, `/api/domains/check-allowed`, `/api/domains/{domain_id}/verify`
- Payments: `/api/payments/create-order`, `/api/payments/create-trial-order`, `/api/payments/verify`
- Developer API: `/api/developer/keys`, `/api/developer/links`, `/api/developer/links/batch`
- Support and sales: `/api/support`, `/contact-sales`

## Environment Variables

The application expects configuration through environment variables loaded from `.env`.

### Required for core app

- `DB_PATH`: SQLAlchemy/PostgreSQL connection string.
- `JWT_SECRET_KEY`: secret used to sign session JWT cookies.

### Redis and background processing

- `REDIS_HOST`: Redis host. Defaults to `127.0.0.1`.
- `REDIS_PORT`: Redis port. Defaults to `6379`.
- `CLICK_FLUSH_INTERVAL`: ARQ click flush cron interval in seconds.
- `GEO_CACHE_TTL`: Geo lookup cache TTL in seconds.
- `CLICK_BATCH_SIZE`: batch-related worker tuning value.
- `REDIS_LOCK_TIMEOUT`: distributed lock TTL for click flush jobs.
- `GEO_IP_TIMEOUT`: timeout for Geo-IP lookups.
- `WEBHOOK_TIMEOUT`: timeout for webhook delivery.

### Authentication

- `FIREBASE_ADMIN_SDK_JSON`: path to the Firebase Admin service account JSON file.

### Link validation and safety

- `SAFE_BROWSING`: Google Safe Browsing API key or configured value used by the validation layer.

### Payments

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`

### Email and notifications

- `RESEND_API_KEY`
- `ADMIN_EMAIL`
- `QUOTATIONS_JSON_PATH`: optional local path for sales quote storage.
- `SUPPORT_JSON_PATH`: optional local path for support ticket storage.

### Custom domains

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ZONE_ID`

### Logging

- `LOG_LEVEL`: defaults to `INFO`.

## Local Development

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install frontend build tooling

```bash
npm install
```

### 3. Configure environment

Create a `.env` file with the required values for PostgreSQL, JWT signing, Firebase, and any optional integrations you want to use locally.

At minimum, local development typically needs:

```env
DB_PATH=postgresql://USER:PASSWORD@HOST:5432/DBNAME
JWT_SECRET_KEY=replace-this
FIREBASE_ADMIN_SDK_JSON=flexurlapp-firebase-adminsdk-fbsvc-0f69d23372.json
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

### 4. Build Tailwind CSS

```bash
npm run build:css
```

The backend also attempts to compile Tailwind automatically on startup if Node and `npx` are available.

### 5. Run the API server

```bash
uvicorn backend.app:app --reload
```

### 6. Run the ARQ worker

```bash
arq backend.arq_worker.WorkerSettings
```

## Data Model Summary

The current schema centers around these tables:

- `users`: local account records mapped to Firebase-authenticated identities
- `urldata`: shortened links, ownership, premium controls, and lifecycle state
- `clicklog`: per-redirect analytics events
- `custom_domains`: branded domain ownership and verification state
- `subscriptions`: plan period, grace-period, and dunning state
- `api_keys`: hashed developer API keys

`init_db()` creates tables and also applies several compatibility-oriented `ALTER TABLE` statements on startup for existing deployments.

## Operational Notes

- Redis is used for rate limiting, analytics buffering, API key caching, Geo-IP caching, and background coordination.
- The app starts a background daily scheduler inside the FastAPI lifespan hook.
- HTML pages are served directly from `frontend/`, and static assets are mounted at `/static`.
- Session auth is cookie-based for browser flows, while the developer API uses bearer or `X-API-Key` credentials.
- Several premium features degrade gracefully if optional integrations are unavailable, but billing, custom domains, email delivery, and safety checks require their corresponding external services.

## Testing

The repository currently includes targeted Python tests such as:

- `test_redirects.py`
- `test_expiration_policy.py`
- `backend/test_inputs.py`

Run them with:

```bash
pytest
```

## Deployment Considerations

- Place FastAPI behind a reverse proxy such as Nginx.
- Run PostgreSQL and Redis as external services.
- Run the ARQ worker separately from the web process.
- Configure Cloudflare correctly if branded domains are enabled.
- Ensure secure production values for JWT, Firebase credentials, email delivery, and payment secrets.

## Current Status

This README reflects the implementation currently present in the repository as of July 16, 2026. It documents the existing product surface and infrastructure dependencies rather than an aspirational roadmap.
