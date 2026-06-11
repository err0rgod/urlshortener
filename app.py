from fastapi import FastAPI
from short_url_gen import add_url, serve_url


app = FastAPI()


@app.get("/")
async def home_page(long_url : str | None = None):
    if long_url:
        short_url = add_url(long_url)
        return short_url
    else:
        return "URL Shortener"
    

@app.get("/short/")
async def give_short(short_url : str | None = None):
    if short_url:
        long_url = serve_url(short_url)
        return long_url
    else:
        return "URL Shortener"
