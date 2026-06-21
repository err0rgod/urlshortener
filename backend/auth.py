from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import jwt
import httpx
import time
from database import get_user_by_email, create_user
import os
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
GOOGLE_REDIRECT_URL = "http://localhost:8000/auth/google/callback"


@router.get("/auth/login/google")
async def google_login():
    """
    Step A: Redirect the user to Google's OAuth consent screen.
    """
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URL}"
        f"&scope=openid%20profile%20email"
        f"&prompt=select_account"
    )
    return RedirectResponse(google_auth_url)


@router.get("/auth/google/callback")
async def google_callback(code : str , response : RedirectResponse):
    """
    Step B: Handle Google redirection, exchange the auth code for a profile,
    and sign a JWT token.
    """
    if not code :
        raise HTTPException(status_code=400, detail= "Authorization code missing.")

    # exchange auth code for access token 
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URL,
        "grant_type":"authorization_code",
    } 

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url,data=token_data)
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token.")
        
        tokens = token_resp.json()
        access_token = tokens.get("access_token")

        # getting userinfo using the access token 
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization":f"Bearer {access_token}"}
        userinfo_resp = await client.get(userinfo_url,headers=headers)
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch User profile.")
        
        profile = userinfo_resp.json()

    email = profile.get("email")
    full_name = profile.get("name", "User")
    oauth_id = profile.get("sub")

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by google account.")
    user = get_user_by_email(email)
    if not user:
        user = create_user(
            email=email,
            full_name=full_name,
            oauth_provider="google",
            oauth_id=oauth_id
        )

    # generate session jwt bro 
    payload = {
        "user_id" : user.id,
        "email" : user.email,
        "exp": time.time() + 604800 # long lasting - 7 days
    }

    sesison_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

    # redirect home and set the Jwt in httpOnly 
    redirect_response = RedirectResponse(url="/")
    redirect_response.set_cookie(
        key="session_token",
        value=sesison_token,
        httponly=True,
        max_age=604800,
        samesite="lax",
        secure=False
    )
    return redirect_response


@router.get("/auth/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie(key="session_token")
    return response

@router.get("/auth/me")
async def get_me(request : Request):
    """
    Check if user is authenticated.
    """
    token = request.cookies.get("session_token")
    if not token:
         return {"logged_in": False}
    try:
        payload = jwt.decode(token,JWT_SECRET_KEY,algorithms=["HS256"])
        email = payload.get("email")

        user = get_user_by_email(email)
        if not user:
            return {"logged_in": False}
        
        return {
            "logged_in": True,
            "user" : {
                "id" : user.id,
                "email" : user.email,
                "full_name" : user.full_name
            }
        }
    except jwt.PyJWTError:
        return {"logged_in":False}