import httpx
import asyncio

async def test_shorten(url):
    payload = {"long_url": url}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post("http://localhost:8000/shorten", json=payload)
            print(f"URL: {url[:50]}... | Status: {resp.status_code} | Response: {resp.text}")
        except Exception as e:
            print(f"URL: {url[:50]}... | Failed: {e}")

async def main():
    test_urls = [
        "https://google.com",              # Valid
        "not-a-url",                       # Invalid format
        "http://this-does-not-exist.xyz",  # Valid format, but dead link
        "http://127.0.0.1",                # Potential SSRF
        "",                                # Empty
        "https://" + "a" * 2000 + ".com"   # Extremely long
    ]
    
    print("Testing inputs (Ensure server is running on localhost:8000)...")
    for url in test_urls:
        await test_shorten(url)

if __name__ == "__main__":
    asyncio.run(main())
