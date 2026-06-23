import httpx
from urllib.parse import urlparse

def parse_user_agent(user_agent : str):
    """
    parse User agent string to determine device type and Browser.
    """
    ua = user_agent.lower()
    # detect device category
    if "ipad" in ua or ("android" in ua and "mobile" not in ua):
        device = "Tablet"
    elif "mobi" in ua or "iphone" in ua or "ipod" in ua:
        device = "Mobile"
    else:
        device = "Desktop"

    # detect browser type
    if "opr" in ua or "opera" in ua:
        browser = "Opera"
    elif "edg" in ua:
        browser = "Edge"
    elif "chrome" in ua:
        browser = "Chrome"
    elif "safari" in ua:
        browser = "Safari"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "msie" in ua or "trident" in ua:
        browser = "Internet Explorer"
    else:
        browser = "Unknown"    
    return browser, device

def parse_referer(referer_header : str) -> str:
    """parse referer header to extract domain and clean redirect"""
    if not referer_header or referer_header == "Direct":
        return "Direct/Email"
    try:
        parsed = urlparse(referer_header)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        if domain in ("t.co","x.com","twitter.com"):
            return "X/Twitter"
        
        if "google" in domain:
            return "Google"
        if "linkedin" in domain:
            return "Linkedin"
        if "github" in domain:
            return "Github"
        if "facebook" in domain:
            return "Facebook"
        if "reddit" in domain:
            return "Reddit"
        
        return domain if domain else "Direct/Email"
    except:
        return "Direct/Email"
    
async def get_ip_country(ip : str)-> str:
    if ip in ("127.0.0.1",":1","localhost") or ip.startswith("192.168") or ip.startswith("10."):
        return "Local/Internal"
    url = f"https://freeapi.com/api/json/{ip}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url,timeout=2.0)
            if response.status_code == 200:
                data=response.json()
                return data.get("countryname","Unkwonw")
        except:
            pass
        return "Unknown"
