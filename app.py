from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from short_url_gen import add_url, serve_url, ban_in_cache
from database import mark_url_banned
from validations import is_valid_url, check_safe_browsing
from ratelimit import RateLimiterStore
import time

app = FastAPI()
limiter = RateLimiterStore(max_tokens=10,refill_rate=1, interval=1)

@app.middleware("http")
async def rate_limit_middleware(request : Request, call_next):
    client_ip = request.client.host
    bucket = limiter.get_bucket(client_ip)
    if not bucket.allow_request():
        retry_after = bucket.get_reset_time()- time.time()
        return JSONResponse(
            status_code=429,
            content={"detail":"Too many requests. Try again later."},
            headers={
                "Retry-After":str(max(1, int(retry_after))),
                "X-RateLimit-Limit":str(bucket.max_tokens),
                "X-RateLimit-Remaining":str(bucket.get_remaining()),
                "X-RateLimit-Reset": str(int(bucket.get_reset_time))
            },
        )
    
    # if valid return normal
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"]=str(bucket.max_tokens)
    response.headers["X-RateLimit-Remaining"]=str(bucket.get_remaining)
    response.headers["X-RateLimit-Reset"]=str(bucket.get_reset_time)
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
    with open("templates/index.html") as f:
        return f.read()

@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    with open("templates/privacy.html") as f:
        return f.read()

@app.get("/{short_url}")
async def get_short_give_long(short_url: str):
    try:
        long_url = serve_url(short_url)
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporary unavailable")
        
    if long_url == "BANNED":
        with open("templates/banned.html") as f:
            return HTMLResponse(content=f.read(), status_code=403)
            
    if long_url:
        return RedirectResponse(long_url, status_code=302)
    raise HTTPException(status_code=404, detail="Short URL not found")

@app.post("/shorten")
async def add_long_give_short(request: URLRequest, req: Request, background_tasks: BackgroundTasks):
    long_url = request.long_url
    
    if not await is_valid_url(long_url):
        raise HTTPException(status_code=400, detail="Invalid, insecure, or private URL")
        
    try:
        short_code = add_url(long_url)
    except Exception:
         raise HTTPException(status_code=500, detail="Failed to generate short URL")
    
    # Trigger Safe Browsing check in the background
    background_tasks.add_task(background_safe_browsing_check, short_code, long_url)
    
    # Construct the full short URL using the request base URL
    base_url = str(req.base_url).rstrip("/")
    full_short_url = f"{base_url}/{short_code}"
    
    return {"short_url": full_short_url}
