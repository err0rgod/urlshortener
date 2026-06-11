from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from short_url_gen import add_url, serve_url
from validations import is_valid_url

app = FastAPI()

class URLRequest(BaseModel):
    long_url: str



@app.get("/", response_class=HTMLResponse)
async def index():  
    with open("templates/index.html") as f:
        return f.read()

@app.get("/{short_url}")
async def get_short_give_long(short_url: str):
    long_url = serve_url(short_url)
    if long_url:
        return RedirectResponse(long_url, status_code=302)
    raise HTTPException(status_code=404, detail="Short URL not found")

@app.post("/shorten")
async def add_long_give_short(request: URLRequest, req: Request):
    long_url = request.long_url
    
    if not is_valid_url(long_url):
        raise HTTPException(status_code=400, detail="Invalid or insecure URL")
        
    short_code = add_url(long_url)
    # Construct the full short URL using the request base URL
    base_url = str(req.base_url).rstrip("/")
    full_short_url = f"{base_url}/{short_code}"
    
    return {"short_url": full_short_url}
