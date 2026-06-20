from pydantic import AnyHttpUrl, ValidationError, TypeAdapter
import httpx
import os
import ipaddress
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()
SAFE_BROWSING = os.getenv("SAFE_BROWSING")

async def check_safe_browsing(url: str) -> bool:
    payload = {
        "uris": [url],
        "threatTypes": [
            "MALWARE",
            "SOCIAL_ENGINEERING",
            "UNWANTED_SOFTWARE",
            "MALICIOUS_BINARY"
        ]
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"https://safebrowsing.googleapis.com/v5/uris:batchGet",
                params={"key": SAFE_BROWSING},
                json=payload,
                timeout=5
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("threats"):
                return False

            return True

        except Exception:
            # Fallback to safe if API is down to avoid blocking user flow
            return True

async def is_live_url(url: str) -> bool:
    async with httpx.AsyncClient() as client:
        try: 
            # We use a 2s timeout here to keep response times fast
            response = await client.head(url, timeout=2.0, follow_redirects=True)
            return response.status_code < 500
        except Exception:
            return False 

def is_private_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return True

        # Check if it's an IP address and if it's private
        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_private or ip.is_loopback
        except ValueError:
            # Not an IP, could be localhost or a local hostname
            if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
                return True
            return False
    except Exception:
        return True

async def is_valid_url(url: str) -> bool:
    adapter = TypeAdapter(AnyHttpUrl)
    try:
        adapter.validate_python(url)

        # Block internal/private network access (SSRF protection)
        if is_private_url(url):
            return False

        return await is_live_url(url)
    except ValidationError:
        return False