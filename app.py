from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
from short_url_gen import add_url, serve_url


app = FastAPI()


@app.get("/",response_class=HTMLResponse)
async def index():  
    with open("templates/index.html") as f:
        return f.read()


@app.get("/{short_url}")
async def get_short_give_long(short_url : str | None = None):
    
    long_url = serve_url(short_url)
    return RedirectResponse(long_url,status_code=302)
    
@app.post(f"/")
async def add_long_give_short(long_url : str | None = None):
    if long_url:
        short_url = add_url(long_url)
        return short_url
    else:
        with open("templates/shortened.html") as f:
            return f.read()
    

