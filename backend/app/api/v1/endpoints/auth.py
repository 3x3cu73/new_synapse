from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.core.security import create_access_token, create_refresh_token, ALGORITHM
from app.core.config import settings
from app.schemas.user import UserOut
from jose import jwt, JWTError
import logging
import secrets
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

REFRESH_COOKIE_KEY = "refresh_token"
CSRF_COOKIE_KEY = "csrf_token"


def _set_refresh_cookie(response: Response, token: str):
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def _set_csrf_cookie(response: Response, csrf_token: str):
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=CSRF_COOKIE_KEY,
        value=csrf_token,
        httponly=False,
        secure=is_prod,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


def _verify_csrf(request: Request):
    cookie_token = request.cookies.get(CSRF_COOKIE_KEY)
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(status_code=403, detail="CSRF validation failed")


@router.post("/refresh")
@limiter.limit("30/minute")
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(deps.get_db)
):
    """Use the refresh token cookie to get a new access token."""
    _verify_csrf(request)

    token = request.cookies.get(REFRESH_COOKIE_KEY)
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access = create_access_token(subject=user.id)
    new_refresh = create_refresh_token(subject=user.id)
    new_csrf = secrets.token_urlsafe(32)
    _set_refresh_cookie(response, new_refresh)
    _set_csrf_cookie(response, new_csrf)

    return {"access_token": new_access, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    """Clear the refresh token and CSRF cookies."""
    response.delete_cookie(
        key=REFRESH_COOKIE_KEY,
        path="/api/v1/auth",
    )
    response.delete_cookie(
        key=CSRF_COOKIE_KEY,
        path="/",
    )
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
def read_users_me(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """Fetch the current user with roles (synced from Superdirectory when configured)."""
    from sqlalchemy.orm import joinedload

    from app.core.config import settings as app_settings
    from app.models.role import Role
    from app.services.superdir_sync import sync_user_from_superdir

    if app_settings.REDPAGE_SYNC_ON_ME and app_settings.REDPAGE_API_BASE:
        sync_user_from_superdir(db, current_user)

    user = (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.organization))
        .filter(User.id == current_user.id)
        .first()
    )
    return user
