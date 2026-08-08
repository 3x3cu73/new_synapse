"""DevClub IITD OIDC login/callback mounted at /api/auth/*."""
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.enums import HostelName
from app.models.user import User
from app.services.oidc_auth import (
    build_authorization_url,
    create_oauth_state,
    exchange_code_for_tokens,
    extract_email,
    extract_entry_number,
    extract_full_entry_number,
    extract_hostel,
    extract_kerberos,
    extract_name,
    fetch_userinfo,
    get_oidc_config,
    pop_oauth_state,
)
from app.utils.entry_number import parse_entry_number

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["oidc"])

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


def _parse_hostel(raw: str | None) -> HostelName | None:
    if not raw:
        return None
    normalized = raw.strip()
    for hostel in HostelName:
        if hostel.value.lower() == normalized.lower():
            return hostel
    # common variants
    aliases = {
        "day scholar": HostelName.DAYSCHOLAR,
        "day-scholar": HostelName.DAYSCHOLAR,
    }
    return aliases.get(normalized.lower())


@router.get("/login")
async def oidc_login():
    if not settings.OIDC_CLIENT_ID or not settings.OIDC_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OIDC is not configured. Set OIDC_CLIENT_ID and OIDC_CLIENT_SECRET.",
        )

    oauth_state = create_oauth_state()
    config = await get_oidc_config()
    authorization_url = build_authorization_url(
        config, oauth_state.state, oauth_state.code_verifier
    )
    return RedirectResponse(url=authorization_url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
async def oidc_callback(
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(deps.get_db),
):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    oauth_state = pop_oauth_state(state)
    if not oauth_state:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        config = await get_oidc_config()
        token = await exchange_code_for_tokens(
            config, code, oauth_state.code_verifier
        )
        userinfo = await fetch_userinfo(config, token["access_token"])
    except Exception as exc:
        logger.exception("OIDC token exchange failed: %s", exc)
        raise HTTPException(status_code=401, detail="OIDC authentication failed") from exc

    kerberos = extract_kerberos(userinfo)
    if not kerberos:
        raise HTTPException(status_code=400, detail="Could not determine kerberos ID")

    email = extract_email(userinfo, kerberos)
    name = extract_name(userinfo)
    # Unique id stored as kerberos (ms1240098), not full 2024MS10098 entry.
    entry_number = extract_entry_number(userinfo, kerberos)
    full_entry = extract_full_entry_number(userinfo)
    hostel = _parse_hostel(extract_hostel(userinfo))
    dept, year = parse_entry_number(full_entry or entry_number)

    # Prefer kerberos match (canonical), then email.
    user = db.query(User).filter(User.entry_number == entry_number).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            email=email,
            name=name,
            entry_number=entry_number,
            department=dept,
            current_year=year,
            hostel=hostel,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        if name and user.name != name:
            user.name = name
            changed = True
        # Migrate legacy full entry numbers → kerberos
        if entry_number and user.entry_number != entry_number:
            user.entry_number = entry_number
            changed = True
        if email and user.email != email and not str(user.email).endswith("@iitd.ac.in"):
            pass  # keep dept email if already set
        elif email and user.email != email:
            user.email = email
            changed = True
        if dept and user.department != dept:
            user.department = dept
            changed = True
        if year and user.current_year != year:
            user.current_year = year
            changed = True
        if hostel and user.hostel != hostel:
            user.hostel = hostel
            changed = True
        if changed:
            db.commit()
            db.refresh(user)

    # Sync Superdir roles immediately so the first /auth/me already has dashboards
    try:
        from app.services.superdir_sync import sync_user_from_superdir

        sync_user_from_superdir(db, user)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Post-login Superdir sync failed for %s: %s", user.email, exc)

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    csrf_token = secrets.token_urlsafe(32)

    redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/callback#access_token={access_token}"
    redirect = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    _set_refresh_cookie(redirect, refresh_token)
    _set_csrf_cookie(redirect, csrf_token)
    return redirect
