import sys
import os

# Ensure the backend directory is in python path for local imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from short_url_gen import add_url, serve_url, ban_in_cache,add_custom_url
from database import mark_url_banned, init_db
from validations import is_valid_url, check_safe_browsing
from ratelimit import RateLimiterStore
from auth import router as auth_router
from typing import Optional
import time
import jwt

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

init_db()

FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

app = FastAPI()
app.include_router(auth_router)
limiter = RateLimiterStore(max_tokens=10,refill_rate=6, interval=60)


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

@app.get("/{short_url}")
async def get_short_give_long(short_url: str):
    try:
        long_url = serve_url(short_url)
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporary unavailable")

    if long_url == "BANNED":
        with open(os.path.join(FRONTEND_DIR, "banned.html"), encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=403)
            
    if long_url:
        return RedirectResponse(long_url, status_code=302)
    raise HTTPException(status_code=404, detail="Short URL not found")

@app.post("/shorten")
async def add_long_give_short(request: URLRequest, req: Request, background_tasks: BackgroundTasks, custom_alias: Optional[str] = None , exp_time: Optional[int] = None):
    long_url = request.long_url
    
    if not await is_valid_url(long_url):
        raise HTTPException(status_code=400, detail="Invalid, insecure, or private URL")
        
    # Extract user_id if user is authenticated
    user_id = None
    token = req.cookies.get("session_token")
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
        except jwt.PyJWTError:
            pass
        
    try:
        if custom_alias:
            short_code = add_custom_url(long_url,custom_alias,user_id=user_id,exp_time=exp_time)
        else:
            short_code = add_url(long_url, user_id=user_id,exp_time=exp_time)
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
