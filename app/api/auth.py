import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from httpx_oauth.clients.github import GitHubOAuth2
from typing import Optional

from app.config import get_settings
from app.db.session import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()

github_oauth_client = GitHubOAuth2(
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")
    return encoded_jwt

def _get_base_url(request: Request) -> str:
    """Get the real external base URL, respecting proxy/ngrok headers."""
    # Check for forwarded headers (ngrok, reverse proxies)
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    forwarded_host = request.headers.get("x-forwarded-host", "") or request.headers.get("host", "")
    
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}/"
    
    return str(request.base_url)

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = request.cookies.get("session")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        sub = payload.get("sub")
        if sub is None:
            return None
        user_id = int(sub)
    except Exception as e:
        logger.warning(f"Failed to decode session token: {e}")
        return None
        
    return db.query(User).filter(User.id == user_id).first()


@router.get("/github/login")
async def github_login(request: Request):
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
        
    base_url = _get_base_url(request)
    redirect_uri = base_url + "auth/github/callback"
    authorization_url = await github_oauth_client.get_authorization_url(
        redirect_uri=redirect_uri,
        scope=["user:email", "read:user"],
    )
    return RedirectResponse(authorization_url)


@router.get("/github/callback")
async def github_callback(request: Request, code: str, db: Session = Depends(get_db)):
    base_url = _get_base_url(request)
    redirect_uri = base_url + "auth/github/callback"
    
    try:
        access_token = await github_oauth_client.get_access_token(code, redirect_uri)
        token = access_token["access_token"]
        
        # Get user info
        import httpx
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
            user_response = await client.get("https://api.github.com/user", headers=headers)
            user_response.raise_for_status()
            user_data = user_response.json()
            
        github_id = user_data["id"]
        username = user_data["login"]
        avatar_url = user_data.get("avatar_url", "")
        
        # Update or create user
        user = db.query(User).filter(User.github_id == github_id).first()
        if user:
            user.username = username
            user.avatar_url = avatar_url
        else:
            user = User(github_id=github_id, username=username, avatar_url=avatar_url)
            db.add(user)
            
        db.commit()
        db.refresh(user)

        # Link any existing installations for this user
        try:
            from app.db.models import AppInstallation
            from sqlalchemy import func
            installs = db.query(AppInstallation).filter(
                func.lower(AppInstallation.account_name) == username.lower()
            ).all()
            for inst in installs:
                inst.user_id = user.id

            # Sync from GitHub App if available
            if settings.github_app_id and settings.github_private_key:
                import github
                pk = settings.github_private_key.replace("\\n", "\n")
                gi = github.GithubIntegration(int(settings.github_app_id), pk)
                for inst in gi.get_installations():
                    acc = inst.raw_data.get("account", {})
                    acc_login = acc.get("login", "")
                    if acc_login.lower() == username.lower():
                        existing = db.query(AppInstallation).filter(AppInstallation.installation_id == inst.id).first()
                        if existing:
                            existing.user_id = user.id
                            existing.account_name = acc_login
                        else:
                            db.add(AppInstallation(
                                installation_id=inst.id,
                                target_id=acc.get("id", 0),
                                target_type=acc.get("type", "User"),
                                account_name=acc_login,
                                user_id=user.id,
                            ))
            db.commit()
        except Exception as e:
            logger.warning(f"Could not link installations for {username}: {e}")
        
        # Create session (sub MUST be a string for JWT standard)
        jwt_token = create_access_token(data={"sub": str(user.id)})
        
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="session", 
            value=jwt_token, 
            httponly=True, 
            max_age=7*24*60*60,
            samesite="lax",
            path="/",
        )
        return response
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session", path="/")
    return response
