from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oauth2.rfc7636 import create_s256_code_challenge

from app.core.config import settings


@dataclass
class OAuthState:
    state: str
    code_verifier: str


_oauth_states: dict[str, OAuthState] = {}
_oidc_config_cache: dict[str, Any] | None = None


def create_oauth_state() -> OAuthState:
    import secrets

    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    oauth_state = OAuthState(state=state, code_verifier=code_verifier)
    _oauth_states[state] = oauth_state
    return oauth_state


def pop_oauth_state(state: str) -> OAuthState | None:
    return _oauth_states.pop(state, None)


async def get_oidc_config() -> dict[str, Any]:
    global _oidc_config_cache
    if _oidc_config_cache is not None:
        return _oidc_config_cache

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(settings.OIDC_DISCOVERY_URL)
        response.raise_for_status()
        _oidc_config_cache = response.json()
        return _oidc_config_cache


def build_authorization_url(config: dict[str, Any], state: str, code_verifier: str) -> str:
    challenge = create_s256_code_challenge(code_verifier)
    params = {
        "response_type": "code",
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "scope": settings.OIDC_SCOPE,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{config['authorization_endpoint']}?{urlencode(params)}"


async def exchange_code_for_tokens(
    config: dict[str, Any], code: str, code_verifier: str
) -> dict[str, Any]:
    async with AsyncOAuth2Client(
        client_id=settings.OIDC_CLIENT_ID,
        client_secret=settings.OIDC_CLIENT_SECRET,
    ) as client:
        return await client.fetch_token(
            config["token_endpoint"],
            code=code,
            redirect_uri=settings.OIDC_REDIRECT_URI,
            code_verifier=code_verifier,
            grant_type="authorization_code",
        )


async def fetch_userinfo(config: dict[str, Any], access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            config["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def extract_kerberos(userinfo: dict[str, Any]) -> str | None:
    for key in ("preferred_username", "kerberos", "sub", "username"):
        value = userinfo.get(key)
        if isinstance(value, str) and value.strip():
            kerberos = value.strip().split("@")[0].lower()
            if kerberos:
                return kerberos
    email = userinfo.get("email")
    if isinstance(email, str) and "@" in email:
        return email.split("@")[0].lower()
    return None


def extract_name(userinfo: dict[str, Any]) -> str:
    for key in ("name", "given_name", "preferred_username"):
        value = userinfo.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Unknown User"


def extract_email(userinfo: dict[str, Any], kerberos: str) -> str:
    email = userinfo.get("email")
    if isinstance(email, str) and "@" in email:
        return email.lower().strip()
    return f"{kerberos}@iitd.ac.in"


def extract_full_entry_number(userinfo: dict[str, Any]) -> str | None:
    """Optional full IITD entry (e.g. 2024MS10098) for dept/year parsing only."""
    for key in ("entry_number", "entryNumber"):
        value = userinfo.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    return None


def extract_entry_number(userinfo: dict[str, Any], kerberos: str) -> str:
    """
    Synapse unique id = kerberos (e.g. ms1240098), matching Superdir.
    Do not store full 2024… entry numbers as the user key.
    """
    return kerberos.lower().strip()


def extract_hostel(userinfo: dict[str, Any]) -> str | None:
    value = userinfo.get("hostel")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
