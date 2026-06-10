from fastapi import FastAPI
from short_url_gen import get_short_url


app = FastAPI()


@app.get("/")
async def home_page(long_url : str | None = None):
    short_url = get_short_url(long_url)
    return short_url