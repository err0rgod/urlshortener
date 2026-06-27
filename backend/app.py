import sys
import os
import json
import asyncio

# Ensure the backend directory is in python path for local imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Response
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from short_url_gen import add_url, serve_url, ban_in_cache,add_custom_url
from database import mark_url_banned, init_db, add_clicklog, engine
from validations import is_valid_url, check_safe_browsing, is_valid_custom_alias
from ratelimit import RateLimiterStore
from auth import router as auth_router
from quotation import process_quotation
from models import clicklog, urldata, User
from analytics_parser import parse_referer, parse_user_agent, get_ip_country, get_ip_location, check_is_bot
from typing import Optional
import time
import jwt
from sqlmodel import Session, select
from sqlalchemy import func
from contextlib import asynccontextmanager
from logger import logger
from report_scheduler import daily_report_scheduler_loop

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

init_db() #for initialising table structure

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    logger.info("Launching background daily report scheduler...")
    scheduler_task = asyncio.create_task(daily_report_scheduler_loop())
    yield
    logger.info("Application shutting down...")
    logger.info("Canceling background report scheduler task...")
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    logger.info("Application shutdown completed.")


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)

limiter = RateLimiterStore(max_tokens=60, refill_rate=60, interval=60)


@app.middleware("http")
async def rate_limit_middleware(request : Request, call_next):
    client_ip = request.client.host
    bucket = limiter.get_bucket(client_ip)
    if not bucket.allow_request():
        retry_after = bucket.get_reset_time()- time.time()
        accept_header = request.headers.get("accept", "")
        
        if "text/html" in accept_header:
            return HTMLResponse(
                content=f"<html><body><h1>Too Many Requests</h1><p>Please try again after {retry_after:.0f} seconds.</p></body></html>",
                status_code=429
            )
        
        return JSONResponse(
            status_code=429,
            content={"detail": f"Too many requests. Please try again after {retry_after:.0f} seconds."},
            headers={
                "Retry-After":str(max(1, int(retry_after))),
                "X-RateLimit-Limit":str(bucket.max_tokens),
                "X-RateLimit-Remaining":str(bucket.get_remaining()),
                "X-RateLimit-Reset": str(int(bucket.get_reset_time()))
            },
        )
    
    # if valid return normal
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"]=str(bucket.max_tokens)
    response.headers["X-RateLimit-Remaining"]=str(bucket.get_remaining())
    response.headers["X-RateLimit-Reset"]=str(bucket.get_reset_time())
    return response



class URLRequest(BaseModel):
    long_url: str = Field(..., max_length=2048)
    webhook_url: Optional[str] = Field(None, max_length=2048)
    ios_url: Optional[str] = Field(None, max_length=2048)
    android_url: Optional[str] = Field(None, max_length=2048)
    password: Optional[str] = Field(None, max_length=255)
    fallback_url: Optional[str] = Field(None, max_length=2048)


# checks if the url is safe or not, if not marks them as banned in the Database & when a user visits a banned url he see's a banned url page
async def background_safe_browsing_check(short_url: str, long_url: str):
    is_safe = await check_safe_browsing(long_url)
    if not is_safe:
        mark_url_banned(short_url)
        ban_in_cache(short_url)

# serving essesntial SEO files
@app.get("/robots.txt")
async def robots():
    with open(os.path.join(FRONTEND_DIR, "robots.txt"), encoding="utf-8") as f:
        return Response(content=f.read(), media_type="text/plain")
@app.get("/sitemap.xml")
async def sitemap():
    with open(os.path.join(FRONTEND_DIR, "sitemap.xml"), encoding="utf-8") as f:
        return Response(content=f.read(), media_type="application/xml")
@app.get("/security.txt")
@app.get("/.well-known/security.txt")
async def security():
    with open(os.path.join(FRONTEND_DIR, "security.txt"), encoding="utf-8") as f:
        return Response(content=f.read(), media_type="text/plain")


# main website returns the index page
@app.get("/", response_class=HTMLResponse)
async def index():  
    with open(os.path.join(FRONTEND_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()

# essential legal files
@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    with open(os.path.join(FRONTEND_DIR, "privacy.html"), encoding="utf-8") as f:
        return f.read()
@app.get("/terms", response_class=HTMLResponse)
async def terms():
    with open(os.path.join(FRONTEND_DIR, "terms.html"), encoding="utf-8") as f:
        return f.read()


# login endpoint 
@app.get("/login", response_class=HTMLResponse)
async def login():
    with open(os.path.join(FRONTEND_DIR, "login.html"), encoding="utf-8") as f:
        return f.read()

# contact page for custom quotes from startups and teams
@app.get("/contact", response_class=HTMLResponse)
async def contact():
    with open(os.path.join(FRONTEND_DIR, "contact.html"), encoding="utf-8") as f:
        return f.read()
# Quotesrequest class
class QuoteRequest(BaseModel):
    business_name: str = Field(..., max_length=255)
    primary_contact: str = Field(..., max_length=255)
    alternate_contact: Optional[str] = Field(None, max_length=255)
    cloud_provider: Optional[str] = Field(None, max_length=50)
    demand_desc: str = Field(..., max_length=5000)

# post endpoint for sending the details to admin
@app.post("/contact-sales")
async def contact_sales(quote: QuoteRequest, background_tasks: BackgroundTasks):
    try:
        # Process quotation asynchronously in background tasks (file write + Resend API post)
        background_tasks.add_task(process_quotation, quote.model_dump())
        return {"status": "success", "message": "Quotation submitted successfully"}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process quotation request")

# for gathering analytics 
async def record_analytics(short_url : str, ip_address : str, user_agent : str, referer : str):
    """
    process http metadata and push in DB"""
    from datetime import datetime, UTC
    import httpx

    browser,device = parse_user_agent(user_agent)
    country, city = await get_ip_location(ip_address)
    clean_referer = parse_referer(referer)
    is_bot = check_is_bot(user_agent)
    
    log = clicklog(
        short_url=short_url,
        ip_address=ip_address,
        country=country,
        city=city,
        browser=browser,
        device=device,
        referer=clean_referer,
        is_bot=is_bot
    )
    add_clicklog(log)
    
    # Increment redirection count on the urldata record
    with Session(engine) as db_session:
        statement = select(urldata).where(urldata.short_url == short_url)
        url_entry = db_session.exec(statement).first()
        if url_entry:
            url_entry.click_count += 1
            db_session.add(url_entry)
            db_session.commit()
            db_session.refresh(url_entry)
            
            # Premium Webhook alert delivery
            if url_entry.webhook_url and url_entry.user_id:
                user = db_session.get(User, url_entry.user_id)
                if user and user.tier == "premium":
                    webhook_payload = {
                        "short_url": url_entry.short_url,
                        "long_url": url_entry.long_url,
                        "clicked_at": log.clicked_at.isoformat() if log.clicked_at else datetime.now(UTC).isoformat(),
                        "ip_address": ip_address,
                        "country": country,
                        "city": city,
                        "browser": browser,
                        "device": device,
                        "referer": clean_referer,
                        "is_bot": is_bot
                    }
                    async def send_webhook(url: str, data: dict):
                        async with httpx.AsyncClient() as client:
                            try:
                                await client.post(url, json=data, timeout=5.0)
                            except Exception as e:
                                logger.warning(f"Failed to deliver webhook to {url}: {e}")
                    
                    asyncio.create_task(send_webhook(url_entry.webhook_url, webhook_payload))


# analytics endpoint for specific short url only accessed by owner
@app.get("/api/analytics/{short_url}")
async def get_url_analytics(short_url: str, request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is not None:
            user_id = int(user_id)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    with Session(engine) as db_session:
        # Check if URL exists and user owns it
        statement = select(urldata).where(urldata.short_url == short_url)
        url_entry = db_session.exec(statement).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="Short URL not found")
        if url_entry.user_id is not None and url_entry.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Check if user is premium
        user = db_session.get(User, user_id)
        if not user or user.tier != "premium":
            raise HTTPException(
                status_code=403, 
                detail="Analytics are a premium feature. Please upgrade your subscription."
            )

        # Clicks by date
        by_date_query = db_session.exec(
            select(func.date(clicklog.clicked_at), func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(func.date(clicklog.clicked_at))
            .order_by(func.date(clicklog.clicked_at))
        ).all()
        by_date = [{"date": str(row[0]), "clicks": row[1]} for row in by_date_query]

        # Clicks by browser
        by_browser_query = db_session.exec(
            select(clicklog.browser, func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(clicklog.browser)
        ).all()
        by_browser = [{"browser": row[0], "clicks": row[1]} for row in by_browser_query]

        # Clicks by device
        by_device_query = db_session.exec(
            select(clicklog.device, func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(clicklog.device)
        ).all()
        by_device = [{"device": row[0], "clicks": row[1]} for row in by_device_query]

        # Clicks by country
        by_country_query = db_session.exec(
            select(clicklog.country, func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(clicklog.country)
        ).all()
        by_country = [{"country": row[0], "clicks": row[1]} for row in by_country_query]

        # Clicks by referrer
        by_referer_query = db_session.exec(
            select(clicklog.referer, func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(clicklog.referer)
        ).all()
        by_referer = [{"referer": row[0], "clicks": row[1]} for row in by_referer_query]

        # Total clicks
        total_clicks = db_session.exec(
            select(func.count(clicklog.id)).where(clicklog.short_url == short_url)
        ).one()

        # User premium state check
        user = db_session.get(User, user_id)
        is_premium = (user.tier == "premium") if user else False

        by_city = []
        bot_clicks = 0
        recent_clicks = []
        if is_premium:
            # Premium: City-level Geolocation Breakdown
            by_city_query = db_session.exec(
                select(clicklog.city, func.count(clicklog.id))
                .where(clicklog.short_url == short_url)
                .group_by(clicklog.city)
                .order_by(func.count(clicklog.id).desc())
            ).all()
            by_city = [{"city": row[0], "clicks": row[1]} for row in by_city_query]

            # Premium: Bot clicks
            bot_clicks = db_session.exec(
                select(func.count(clicklog.id))
                .where(clicklog.short_url == short_url)
                .where(clicklog.is_bot == True)
            ).one()

            # Premium: 5 most recent click logs
            recent_logs = db_session.exec(
                select(clicklog)
                .where(clicklog.short_url == short_url)
                .order_by(clicklog.clicked_at.desc())
                .limit(5)
            ).all()
            for log in recent_logs:
                recent_clicks.append({
                    "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
                    "ip_address": log.ip_address,
                    "country": log.country,
                    "city": log.city,
                    "browser": log.browser,
                    "device": log.device,
                    "referer": log.referer,
                    "is_bot": log.is_bot
                })

        return {
            "short_url": url_entry.short_url,
            "long_url": url_entry.long_url,
            "created_at": url_entry.created_at.isoformat() if url_entry.created_at else None,
            "total_clicks": total_clicks,
            "by_date": by_date,
            "by_browser": by_browser,
            "by_device": by_device,
            "by_country": by_country,
            "by_referer": by_referer,
            "by_city": by_city,
            "bot_clicks": bot_clicks,
            "recent_clicks": recent_clicks,
            "is_premium": is_premium
        }

# dashboard endpoint for users who have account auth required
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        return RedirectResponse(url="/login")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
    except jwt.PyJWTError:
        return RedirectResponse(url="/login")
    if not user_id:
        return RedirectResponse(url="/login")
        
    with open(os.path.join(FRONTEND_DIR, "dashboard.html"), encoding="utf-8") as f:
        return f.read()


# gives users recent clicks auth required
@app.get("/api/user/recent-clicks")
async def get_recent_clicks(request: Request, limit: int = 10):
    # Constrain limit to prevent database memory exhaustion
    limit = max(1, min(limit, 100))
    
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is not None:
            user_id = int(user_id)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    with Session(engine) as db_session:
        user_links_stmt = select(urldata.short_url).where(urldata.user_id == user_id)
        user_short_urls = db_session.exec(user_links_stmt).all()
        if not user_short_urls:
            return []

        stmt = (
            select(clicklog)
            .where(clicklog.short_url.in_(user_short_urls))
            .order_by(clicklog.clicked_at.desc())
            .limit(limit)
        )
        logs = db_session.exec(stmt).all()
        
        result = []
        for log in logs:
            result.append({
                "id": log.id,
                "short_url": log.short_url,
                "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
                "ip_address": log.ip_address,
                "country": log.country,
                "browser": log.browser,
                "device": log.device,
                "referer": log.referer
            })
        return result

# lists all the links of the user auth required
@app.get("/api/user/links")
async def get_user_links(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is not None:
            user_id = int(user_id)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    with Session(engine) as db_session:
        statement = select(urldata).where(urldata.user_id == user_id).order_by(urldata.created_at.desc())
        links = db_session.exec(statement).all()
        
        result = []
        for link in links:
            result.append({
                "short_url": link.short_url,
                "long_url": link.long_url,
                "created_at": link.created_at.isoformat() if link.created_at else None,
                "click_count": link.click_count,
                "is_banned": link.is_banned,
                "exp_time": link.exp_time.isoformat() if link.exp_time else None,
                "webhook_url": link.webhook_url,
                "ios_url": link.ios_url,
                "android_url": link.android_url,
                "fallback_url": link.fallback_url,
                "has_password": bool(link.password_hash)
            })
        return result

# export url analytics
@app.get("/api/analytics/{short_url}/export")
async def export_analytics_csv(short_url: str, request: Request):
    import csv
    import io
    from fastapi.responses import StreamingResponse
    
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is not None:
            user_id = int(user_id)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    with Session(engine) as db_session:
        # Check if URL exists and user owns it
        statement = select(urldata).where(urldata.short_url == short_url)
        url_entry = db_session.exec(statement).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="Short URL not found")
        if url_entry.user_id is not None and url_entry.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Verify user has premium access
        user = db_session.get(User, user_id)
        if not user or user.tier != "premium":
            raise HTTPException(status_code=403, detail="CSV export is a Premium feature")

        # Fetch click log entries sorted by click date
        statement = select(clicklog).where(clicklog.short_url == short_url).order_by(clicklog.clicked_at.desc())
        logs = db_session.exec(statement).all()

        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow([
            "Clicked At (UTC)", 
            "IP Address", 
            "Country", 
            "City", 
            "Browser", 
            "Device", 
            "Referer", 
            "Is Bot"
        ])
        
        for log in logs:
            writer.writerow([
                log.clicked_at.isoformat() if log.clicked_at else "NA",
                log.ip_address,
                log.country,
                log.city,
                log.browser,
                log.device,
                log.referer,
                "Yes" if log.is_bot else "No"
            ])
            
        output.seek(0)
        return StreamingResponse(
            io.StringIO(output.getvalue()), 
            media_type="text/csv", 
            headers={"Content-Disposition": f"attachment; filename={short_url}_analytics.csv"}
        )

@app.post("/api/user/toggle-tier")
async def toggle_user_tier(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    with Session(engine) as db_session:
        user = db_session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Enforce that only the admin email can manually toggle tiers
        admin_email = os.getenv("ADMIN_EMAIL")
        if not admin_email or user.email != admin_email:
            raise HTTPException(
                status_code=403, 
                detail="Only the administrator can manually toggle tiers."
            )
        
        # Toggle tier
        user.tier = "premium" if user.tier == "free" else "free"
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return {"status": "success", "tier": user.tier}


# link deletion endpoint
@app.delete("/api/links/{short_url}")
async def delete_link(short_url: str, request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is not None:
            user_id = int(user_id)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    with Session(engine) as db_session:
        statement = select(urldata).where(urldata.short_url == short_url)
        url_entry = db_session.exec(statement).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="Short URL not found")
        if url_entry.user_id is not None and url_entry.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Delete any associated clicklog entries first to prevent foreign key violations
        delete_logs_stmt = db_session.exec(
            select(clicklog).where(clicklog.short_url == short_url)
        ).all()
        for log in delete_logs_stmt:
            db_session.delete(log)

        db_session.delete(url_entry)
        db_session.commit()

        # Delete from Redis
        try:
            from short_url_gen import redis_client
            redis_client.delete(short_url)
        except Exception:
            pass

        return {"status": "success", "message": "Link deleted successfully"}

# user account deletion endpoint
@app.delete("/api/user/account")
async def delete_user_account(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session token")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    with Session(engine) as db_session:
        # Fetch user details
        user = db_session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Delete all links owned by this user
        links = db_session.exec(select(urldata).where(urldata.user_id == user_id)).all()
        for link in links:
            # Delete associated clicklogs
            clicklogs = db_session.exec(select(clicklog).where(clicklog.short_url == link.short_url)).all()
            for log in clicklogs:
                db_session.delete(log)
            db_session.delete(link)
            # Remove link from Redis
            try:
                from short_url_gen import redis_client
                redis_client.delete(link.short_url)
            except Exception:
                pass

        # Store Firebase info before deletion
        oauth_provider = user.oauth_provider
        oauth_id = user.oauth_id

        # Delete user from local database
        db_session.delete(user)
        db_session.commit()

        # Delete from Firebase Auth if firebase UID is available
        if oauth_provider == "firebase" and oauth_id:
            try:
                from firebase_admin import auth as firebase_auth
                firebase_auth.delete_user(oauth_id)
            except Exception as e:
                logger.warning(f"Failed to delete user from Firebase Auth: {e}")

    response = JSONResponse(content={"status": "success", "message": "Account deleted successfully"})
    response.delete_cookie(key="session_token")
    return response


@app.get("/analytics/{short_url}", response_class=HTMLResponse)
async def analytics(short_url: str, request: Request):
    token = request.cookies.get("session_token")
    if not token:
        return RedirectResponse(url="/login")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        if user_id is not None:
            user_id = int(user_id)
    except jwt.PyJWTError:
        return RedirectResponse(url="/login")
    if not user_id:
        return RedirectResponse(url="/login")

    with Session(engine) as db_session:
        # Check if URL exists and user owns it
        statement = select(urldata).where(urldata.short_url == short_url)
        url_entry = db_session.exec(statement).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="Short URL not found")
        if url_entry.user_id is not None and url_entry.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        # Check if user is premium
        user = db_session.get(User, user_id)
        if not user or user.tier != "premium":
            raise HTTPException(
                status_code=403, 
                detail="Analytics are a premium feature. Please upgrade your subscription."
            )

        # Clicks by date
        by_date_query = db_session.exec(
            select(func.date(clicklog.clicked_at), func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(func.date(clicklog.clicked_at))
            .order_by(func.date(clicklog.clicked_at))
        ).all()
        by_date = [{"date": str(row[0]), "clicks": row[1]} for row in by_date_query]

        # Clicks by browser
        by_browser_query = db_session.exec(
            select(clicklog.browser, func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(clicklog.browser)
        ).all()
        by_browser = [{"browser": row[0], "clicks": row[1]} for row in by_browser_query]

        # Clicks by device
        by_device_query = db_session.exec(
            select(clicklog.device, func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(clicklog.device)
        ).all()
        by_device = [{"device": row[0], "clicks": row[1]} for row in by_device_query]

        # Clicks by country
        by_country_query = db_session.exec(
            select(clicklog.country, func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(clicklog.country)
        ).all()
        by_country = [{"country": row[0], "clicks": row[1]} for row in by_country_query]

        # Clicks by referrer
        by_referer_query = db_session.exec(
            select(clicklog.referer, func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(clicklog.referer)
        ).all()
        by_referer = [{"referer": row[0], "clicks": row[1]} for row in by_referer_query]

        # Total clicks
        total_clicks = db_session.exec(
            select(func.count(clicklog.id)).where(clicklog.short_url == short_url)
        ).one()

        # Premium: City-level Geolocation Breakdown
        by_city_query = db_session.exec(
            select(clicklog.city, func.count(clicklog.id))
            .where(clicklog.short_url == short_url)
            .group_by(clicklog.city)
            .order_by(func.count(clicklog.id).desc())
        ).all()
        # User premium state check
        user = db_session.get(User, user_id)
        is_premium = (user.tier == "premium") if user else False

        by_city = []
        bot_clicks = 0
        recent_clicks = []
        if is_premium:
            # Premium: City-level Geolocation Breakdown
            by_city_query = db_session.exec(
                select(clicklog.city, func.count(clicklog.id))
                .where(clicklog.short_url == short_url)
                .group_by(clicklog.city)
                .order_by(func.count(clicklog.id).desc())
            ).all()
            by_city = [{"city": row[0], "clicks": row[1]} for row in by_city_query]

            # Premium: Bot clicks
            bot_clicks = db_session.exec(
                select(func.count(clicklog.id))
                .where(clicklog.short_url == short_url)
                .where(clicklog.is_bot == True)
            ).one()

            # Premium: 5 most recent click logs
            recent_logs = db_session.exec(
                select(clicklog)
                .where(clicklog.short_url == short_url)
                .order_by(clicklog.clicked_at.desc())
                .limit(5)
            ).all()
            for log in recent_logs:
                recent_clicks.append({
                    "clicked_at": log.clicked_at.isoformat() if log.clicked_at else None,
                    "ip_address": log.ip_address,
                    "country": log.country,
                    "city": log.city,
                    "browser": log.browser,
                    "device": log.device,
                    "referer": log.referer,
                    "is_bot": log.is_bot
                })

        analytics_data = {
            "short_url": url_entry.short_url,
            "long_url": url_entry.long_url,
            "created_at": url_entry.created_at.isoformat() if url_entry.created_at else None,
            "total_clicks": total_clicks,
            "by_date": by_date,
            "by_browser": by_browser,
            "by_device": by_device,
            "by_country": by_country,
            "by_referer": by_referer,
            "by_city": by_city,
            "bot_clicks": bot_clicks,
            "recent_clicks": recent_clicks,
            "is_premium": is_premium
        }

    with open(os.path.join(FRONTEND_DIR, "analytics.html"), encoding="utf-8") as f:
        html_content = f.read()

    # Inject statistics data safely preventing JSON script tag injection XSS
    json_str = json.dumps(analytics_data).replace("</", r"<\/").replace("<script", r"<\script")
    injected_js = f"window.__INITIAL_DATA__ = {json_str};"
    html_content = html_content.replace("window.__INITIAL_DATA__ = null;", injected_js)

    return HTMLResponse(content=html_content)


# main redirection endpoint accepts short urls and cheks if they exists or not and redirects them 
@app.get("/{short_url}")
async def get_short_give_long(short_url: str, request : Request, backgroud_tasks : BackgroundTasks):
    try:
        long_url = serve_url(short_url)
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporary unavailable")

    if long_url == "BANNED":
        with open(os.path.join(FRONTEND_DIR, "banned.html"), encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=403)
            
    if long_url == "Expired":
        with open(os.path.join(FRONTEND_DIR, "expired.html"), encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=410)
            
    # Premium dynamic routing fallback check
    if long_url == "DYNAMIC" or long_url is None:
        from datetime import datetime, UTC
        with Session(engine) as db_session:
            statement = select(urldata).where(urldata.short_url == short_url)
            url_entry = db_session.exec(statement).first()
            if not url_entry:
                if long_url == "DYNAMIC":
                    raise HTTPException(status_code=503, detail="Service temporary unavailable")
                raise HTTPException(status_code=404, detail="Short URL not found")
                
            # 1. Expiration check with premium fallback
            is_expired = False
            if url_entry.exp_time:
                exp_utc = url_entry.exp_time.astimezone(UTC).replace(tzinfo=None) if url_entry.exp_time.tzinfo else url_entry.exp_time
                now_utc = datetime.now(UTC).replace(tzinfo=None)
                if exp_utc < now_utc:
                    is_expired = True
                    
            if is_expired:
                # Custom fallback redirect
                if url_entry.fallback_url and url_entry.user_id:
                    user = db_session.get(User, url_entry.user_id)
                    if user and user.tier == "premium":
                        return RedirectResponse(url_entry.fallback_url, status_code=302)
                
                with open(os.path.join(FRONTEND_DIR, "expired.html"), encoding="utf-8") as f:
                    return HTMLResponse(content=f.read(), status_code=410)
                    
            # 2. Safety ban check
            if url_entry.is_banned:
                with open(os.path.join(FRONTEND_DIR, "banned.html"), encoding="utf-8") as f:
                    return HTMLResponse(content=f.read(), status_code=403)
                    
            # 3. Password check
            if url_entry.password_hash and url_entry.user_id:
                user = db_session.get(User, url_entry.user_id)
                if user and user.tier == "premium":
                    cookie_name = f"auth_link_{short_url}"
                    auth_cookie = request.cookies.get(cookie_name)
                    if auth_cookie != url_entry.password_hash:
                        with open(os.path.join(FRONTEND_DIR, "password_gate.html"), encoding="utf-8") as f:
                            return HTMLResponse(content=f.read())
                            
            # 4. OS targeting
            target_url = url_entry.long_url
            if url_entry.user_id:
                user = db_session.get(User, url_entry.user_id)
                if user and user.tier == "premium":
                    user_agent = request.headers.get("user-agent", "").lower()
                    if "iphone" in user_agent or "ipad" in user_agent or "ipod" in user_agent:
                        if url_entry.ios_url:
                            target_url = url_entry.ios_url
                    elif "android" in user_agent:
                        if url_entry.android_url:
                            target_url = url_entry.android_url
                            
            # Trigger analytics
            client_ip = request.client.host
            user_agent = request.headers.get("user-agent", "")
            referer = request.headers.get("referer", "Direct")
            backgroud_tasks.add_task(
                record_analytics, short_url, client_ip, user_agent, referer
            )
            return RedirectResponse(target_url, status_code=302)

    if long_url:
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent","")
        referer = request.headers.get("referer","Direct")
        backgroud_tasks.add_task(
            record_analytics,short_url,client_ip,user_agent,referer
        )
        return RedirectResponse(long_url, status_code=302)
    raise HTTPException(status_code=404, detail="Short URL not found")


# main url shortening feature
@app.post("/shorten")
async def add_long_give_short(request: URLRequest, req: Request, background_tasks: BackgroundTasks, custom_alias: Optional[str] = None , exp_time: Optional[int] = None):
    long_url = request.long_url
    
    if not await is_valid_url(long_url):
        raise HTTPException(status_code=400, detail="Invalid, insecure, or private URL")
        
    if custom_alias:
        if not is_valid_custom_alias(custom_alias):
            raise HTTPException(
                status_code=400, 
                detail="Custom alias must be 3-20 characters long, contain only letters, numbers, dashes or underscores, and cannot be a reserved system route."
            )
        from database import is_alias_exists
        if is_alias_exists(custom_alias):
            raise HTTPException(
                status_code=400,
                detail="Custom alias is already in use. Please choose a different one."
            )
        
    # Extract user_id if user is authenticated
    user_id = None
    user_tier = "free"
    token = req.cookies.get("session_token")
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if user_id is not None:
                user_id = int(user_id)
        except jwt.PyJWTError:
            pass
        
    from datetime import datetime, UTC, timedelta

    if user_id:
        with Session(engine) as db_session:
            db_user = db_session.get(User, user_id)
            if db_user:
                user_tier = db_user.tier

    # Enforce limits for free/anonymous tier
    if user_tier == "free":
        if not user_id:
            # Anonymous creation: max expiration is 1 day (24 hours)
            max_exp = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1)
        else:
            # Registered free accounts: max expiration is 15 days
            max_exp = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=15)

        if exp_time:
            requested_exp = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=exp_time)
            computed_exp_time = min(requested_exp, max_exp)
        else:
            computed_exp_time = max_exp

        # Limit checks for registered users
        if user_id:
            with Session(engine) as db_session:
                one_day_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
                thirty_days_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
                
                daily_count = db_session.exec(
                    select(func.count(urldata.short_url))
                    .where(urldata.user_id == user_id)
                    .where(urldata.created_at >= one_day_ago)
                ).one()
                
                if daily_count >= 10:
                    raise HTTPException(
                        status_code=400,
                        detail="Daily limit reached. Free accounts are limited to 10 URLs per day."
                    )
                
                monthly_count = db_session.exec(
                    select(func.count(urldata.short_url))
                    .where(urldata.user_id == user_id)
                    .where(urldata.created_at >= thirty_days_ago)
                ).one()
                
                if monthly_count >= 100:
                    raise HTTPException(
                        status_code=400,
                        detail="Monthly limit reached. Free accounts are limited to 100 URLs per month."
                    )
        else:
            # Limit checks for anonymous guest users using Redis
            client_ip = req.client.host
            forwarded = req.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
                
            from short_url_gen import redis_client
            redis_key = f"anon_limit:{client_ip}"
            try:
                current_count = redis_client.incr(redis_key)
                if current_count == 1:
                    redis_client.expire(redis_key, 86400) # 24 hours
                
                if current_count > 5:
                    raise HTTPException(
                        status_code=400,
                        detail="Anonymous URL creation limit reached (5 per day). Please create a free account to shorten more links."
                    )
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                # Fallback gracefully if Redis fails
                pass
    else:
        # Premium tier
        if exp_time:
            computed_exp_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=exp_time)
        else:
            computed_exp_time = None

    try:
        # Extract premium parameters if the user is premium
        webhook_url = request.webhook_url if user_tier == "premium" else None
        ios_url = request.ios_url if user_tier == "premium" else None
        android_url = request.android_url if user_tier == "premium" else None
        fallback_url = request.fallback_url if user_tier == "premium" else None

        # SSRF Protection: Validate premium parameters if supplied
        if webhook_url and not await is_valid_url(webhook_url):
            raise HTTPException(status_code=400, detail="Invalid, insecure, or private webhook URL")
        if ios_url and not await is_valid_url(ios_url):
            raise HTTPException(status_code=400, detail="Invalid, insecure, or private iOS redirect URL")
        if android_url and not await is_valid_url(android_url):
            raise HTTPException(status_code=400, detail="Invalid, insecure, or private Android redirect URL")
        if fallback_url and not await is_valid_url(fallback_url):
            raise HTTPException(status_code=400, detail="Invalid, insecure, or private fallback URL")

        password_hash = None
        if request.password and user_tier == "premium":
            import hashlib
            salt = "flexurl_salt_secure_2026"
            password_hash = hashlib.sha256((request.password + salt).encode('utf-8')).hexdigest()

        if custom_alias:
            short_code = add_custom_url(
                long_url, custom_alias, user_id=user_id, exp_time=computed_exp_time,
                webhook_url=webhook_url, ios_url=ios_url, android_url=android_url,
                password_hash=password_hash, fallback_url=fallback_url
            )
        else:
            short_code = add_url(
                long_url, user_id=user_id, exp_time=computed_exp_time,
                webhook_url=webhook_url, ios_url=ios_url, android_url=android_url,
                password_hash=password_hash, fallback_url=fallback_url
            )
        if not short_code:
            raise HTTPException(status_code=500, detail="if this executes, the error is in short url.")
    except Exception:
         raise HTTPException(status_code=500, detail="Failed to generate short URL, Possibly the short url is already in use.")
    
    # Trigger Safe Browsing check in the background
    if short_code:
        background_tasks.add_task(background_safe_browsing_check, short_code, long_url)
    else:
        raise HTTPException(status_code=500,detail="Invalid Shorten URL.")
    # Construct the full short URL using the request base URL
    base_url = str(req.base_url).rstrip("/")
    full_short_url = f"{base_url}/{short_code}"
    
    return {"short_url": full_short_url}


@app.post("/{short_url}")
async def post_password_gate(short_url: str, request: Request):
    # Parse URL encoded form parameters
    body = await request.body()
    from urllib.parse import parse_qs
    params = parse_qs(body.decode("utf-8"))
    submitted_pass = params.get("password", [None])[0]
    
    with Session(engine) as db_session:
        statement = select(urldata).where(urldata.short_url == short_url)
        url_entry = db_session.exec(statement).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="Short URL not found")
            
        import hashlib
        salt = "flexurl_salt_secure_2026"
        hashed = hashlib.sha256(((submitted_pass or "") + salt).encode('utf-8')).hexdigest()
        
        if hashed == url_entry.password_hash:
            response = RedirectResponse(url=f"/{short_url}", status_code=303)
            response.set_cookie(key=f"auth_link_{short_url}", value=hashed, max_age=3600)
            return response
        else:
            return RedirectResponse(url=f"/{short_url}?error=1", status_code=303)



