from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel, Field
from short_url_gen import add_url, serve_url, ban_in_cache
from database import mark_url_banned
from validations import is_valid_url, check_safe_browsing

app = FastAPI()

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
