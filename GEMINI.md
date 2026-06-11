# URL Shortener Project Guidance

## Architecture Overview
- **Backend:** FastAPI (Python 3.10+)
- **Database:** SQLModel / PostgreSQL (Production)
- **Cache:** Redis (Used for redirect speed and banning malicious links)
- **Frontend:** Single-page application using Vanilla JS (fetch API)
- **Security:** 
    - Google Safe Browsing API for link safety.
    - SSRF protection (private IP blocking).
    - Asynchronous background checks for minimal latency.

## Core Workflows

### 1. URL Shortening Flow
- User submits `long_url`.
- System validates URL (length, format, live status, and SSRF check).
- Short code generated (SonyFlake ID + Base62 encoding).
- URL stored in Postgres and cached in Redis.
- **Background Task:** `check_safe_browsing` is triggered. If malicious, the URL is marked as `is_banned` in DB and overwritten with `"BANNED"` in Redis.

### 2. Redirect Flow
- User visits `/{short_code}`.
- System checks Redis first.
- If value is `"BANNED"`, serves `templates/banned.html`.
- If found, redirects (302) to the long URL.
- If not in cache, fetches from Postgres and populates cache.

## Deployment (AWS Lightsail)
- **OS:** Ubuntu 22.04
- **Web Server:** Nginx (Reverse Proxy to port 8000)
- **Process Manager:** Gunicorn with Uvicorn workers
- **Environment:** Managed via `.env` file.
- **Database Migration:** Ensure `is_banned` column is added manually to Postgres.

## Code Conventions
- Use `BackgroundTasks` for heavy external API calls.
- Keep validation logic in `validations.py`.
- Keep database models in `models.py`.
- Use asynchronous functions for all I/O bound operations (HTTP requests, DB calls).

## Author & Socials
- **Author:** Nirbhay Katiyar (err0rgod)
- **GitHub:** github.com/err0rgod
- **X/Twitter:** x.com/err0rgod
- **Medium:** err0rgod.medium.com
