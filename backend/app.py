import sys
import os
import json

# Ensure the backend directory is in python path for local imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from short_url_gen import add_url, serve_url, ban_in_cache,add_custom_url
from database import mark_url_banned, init_db, add_clicklog, engine
from validations import is_valid_url, check_safe_browsing, is_valid_custom_alias
from ratelimit import RateLimiterStore
from auth import router as auth_router
from quotation import process_quotation
from models import clicklog, urldata, User
from analytics_parser import parse_referer, parse_user_agent , get_ip_country
from typing import Optional
import time
import jwt
from sqlmodel import Session, select
from sqlalchemy import func

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

init_db()

FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

app = FastAPI()
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

async def background_safe_browsing_check(short_url: str, long_url: str):
    is_safe = await check_safe_browsing(long_url)
    if not is_safe:
        mark_url_banned(short_url)
        ban_in_cache(short_url)

@app.get("/", response_class=HTMLResponse)
async def index():  
    with open(os.path.join(FRONTEND_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()

@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    with open(os.path.join(FRONTEND_DIR, "privacy.html"), encoding="utf-8") as f:
        return f.read()

@app.get("/login", response_class=HTMLResponse)
async def login():
    with open(os.path.join(FRONTEND_DIR, "login.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/contact", response_class=HTMLResponse)
async def contact():
    with open(os.path.join(FRONTEND_DIR, "contact.html"), encoding="utf-8") as f:
        return f.read()

class QuoteRequest(BaseModel):
    business_name: str = Field(..., max_length=255)
    primary_contact: str = Field(..., max_length=255)
    alternate_contact: Optional[str] = Field(None, max_length=255)
    cloud_provider: Optional[str] = Field(None, max_length=50)
    demand_desc: str = Field(..., max_length=5000)

@app.post("/contact-sales")
async def contact_sales(quote: QuoteRequest, background_tasks: BackgroundTasks):
    try:
        # Process quotation asynchronously in background tasks (file write + Resend API post)
        background_tasks.add_task(process_quotation, quote.model_dump())
        return {"status": "success", "message": "Quotation submitted successfully"}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process quotation request")


async def record_analytics(short_url : str, ip_address : str, user_agent : str, referer : str):
    """
    process http metadata and push in DB"""
    browser,device = parse_user_agent(user_agent)
    country = await get_ip_country(ip_address)
    clean_referer = parse_referer(referer)
    log = clicklog(
        short_url=short_url,
        ip_address=ip_address,
        country=country,
        browser=browser,
        device=device,
        referer=clean_referer
    )
    add_clicklog(log)



@app.get("/api/analytics/{short_url}")
async def get_url_analytics(short_url: str, request: Request):
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
        # Check if URL exists and user owns it
        statement = select(urldata).where(urldata.short_url == short_url)
        url_entry = db_session.exec(statement).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="Short URL not found")
        if url_entry.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

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

        return {
            "short_url": url_entry.short_url,
            "long_url": url_entry.long_url,
            "created_at": url_entry.created_at.isoformat() if url_entry.created_at else None,
            "total_clicks": total_clicks,
            "by_date": by_date,
            "by_browser": by_browser,
            "by_device": by_device,
            "by_country": by_country,
            "by_referer": by_referer
        }

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

@app.get("/api/user/recent-clicks")
async def get_recent_clicks(request: Request, limit: int = 10):
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

@app.get("/api/user/links")
async def get_user_links(request: Request):
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
                "exp_time": link.exp_time.isoformat() if link.exp_time else None
            })
        return result

@app.delete("/api/links/{short_url}")
async def delete_link(short_url: str, request: Request):
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
        statement = select(urldata).where(urldata.short_url == short_url)
        url_entry = db_session.exec(statement).first()
        if not url_entry:
            raise HTTPException(status_code=404, detail="Short URL not found")
        if url_entry.user_id != user_id:
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
                print(f"Warning: Failed to delete user from Firebase Auth: {e}")

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
        if url_entry.user_id != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

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

        analytics_data = {
            "short_url": url_entry.short_url,
            "long_url": url_entry.long_url,
            "created_at": url_entry.created_at.isoformat() if url_entry.created_at else None,
            "total_clicks": total_clicks,
            "by_date": by_date,
            "by_browser": by_browser,
            "by_device": by_device,
            "by_country": by_country,
            "by_referer": by_referer
        }

    with open(os.path.join(FRONTEND_DIR, "analytics.html"), encoding="utf-8") as f:
        html_content = f.read()

    # Inject statistics data safely preventing JSON script tag injection XSS
    json_str = json.dumps(analytics_data).replace("</", r"<\/").replace("<script", r"<\script")
    injected_js = f"window.__INITIAL_DATA__ = {json_str};"
    html_content = html_content.replace("window.__INITIAL_DATA__ = null;", injected_js)

    return HTMLResponse(content=html_content)

@app.get("/{short_url}")
async def get_short_give_long(short_url: str, request : Request, backgroud_tasks : BackgroundTasks):
    try:
        long_url = serve_url(short_url)
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporary unavailable")

    if long_url == "BANNED":
        with open(os.path.join(FRONTEND_DIR, "banned.html"), encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=403)
            
    if long_url:
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent","")
        referer = request.headers.get("referer","Direct")
        backgroud_tasks.add_task(
            record_analytics,short_url,client_ip,user_agent,referer
        )
        return RedirectResponse(long_url, status_code=302)
    raise HTTPException(status_code=404, detail="Short URL not found")





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
        
    # Extract user_id if user is authenticated
    user_id = None
    user_tier = "free"
    token = req.cookies.get("session_token")
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
        except jwt.PyJWTError:
            pass
        
    from datetime import datetime, UTC, timedelta

    if user_id:
        with Session(engine) as db_session:
            db_user = db_session.get(User, user_id)
            if db_user:
                user_tier = db_user.tier

    # Enforce limits for free tier
    if user_tier == "free":
        max_exp = datetime.now(UTC) + timedelta(days=15)
        if exp_time:
            requested_exp = datetime.now(UTC) + timedelta(hours=exp_time)
            computed_exp_time = min(requested_exp, max_exp)
        else:
            computed_exp_time = max_exp

        # Limit checks for registered users
        if user_id:
            with Session(engine) as db_session:
                one_day_ago = datetime.now(UTC) - timedelta(days=1)
                thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
                
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
        # Premium tier
        if exp_time:
            computed_exp_time = datetime.now(UTC) + timedelta(hours=exp_time)
        else:
            computed_exp_time = None

    try:
        if custom_alias:
            short_code = add_custom_url(long_url, custom_alias, user_id=user_id, exp_time=computed_exp_time)
        else:
            short_code = add_url(long_url, user_id=user_id, exp_time=computed_exp_time)
        if not short_code:
            raise HTTPException(status_code=500, detail="if this executes, the error is in short url.")
    except Exception:
        #  import traceback
        #  traceback.print_exc()
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



