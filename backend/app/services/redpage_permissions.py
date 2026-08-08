"""Consume Superdirectory universal permissions (HTTP + RS256 assertion)."""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import jwk, jwt
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

_jwks_cache: dict[str, Any] = {"fetched_at": 0.0, "keys": []}
_JWKS_TTL = 60 * 60


class CapabilityScope(BaseModel):
    allowed: bool = False
    all_clubs: bool = False
    club_ids: list[str] = Field(default_factory=list)


class ClubInfo(BaseModel):
    club_id: str
    name: str
    type: str | None = None
    logo_url: str | None = None
    description: str | None = None


class PermissionsAccess(BaseModel):
    kerberos: str
    name: str
    academic_year: str = ""
    global_level: int | None = None
    club_levels: dict[str, int] = Field(default_factory=dict)
    capabilities: dict[str, CapabilityScope] = Field(default_factory=dict)
    audience: str = "synapse"
    assertion: str = ""
    clubs: list[ClubInfo] = Field(default_factory=list)

    @property
    def is_superadmin(self) -> bool:
        return self.global_level == 0

    def capability(self, name: str) -> CapabilityScope:
        return self.capabilities.get(name) or CapabilityScope()

    def can(self, capability: str, club_id: str | None = None) -> bool:
        scope = self.capability(capability)
        if not scope.allowed and not scope.all_clubs:
            # still allow if all_clubs / * encoded
            if "*" in scope.club_ids or scope.all_clubs:
                return True
            return False
        if scope.all_clubs or "*" in scope.club_ids:
            return True
        if club_id is None:
            return scope.allowed or bool(scope.club_ids)
        return club_id in scope.club_ids


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if settings.REDPAGE_SERVICE_KEY:
        headers["X-Service-Key"] = settings.REDPAGE_SERVICE_KEY
    return headers


def _base() -> str:
    return settings.REDPAGE_API_BASE.rstrip("/")


def _fetch_jwks(client: httpx.Client) -> list[dict[str, Any]]:
    now = time.time()
    if _jwks_cache["keys"] and now - _jwks_cache["fetched_at"] < _JWKS_TTL:
        return _jwks_cache["keys"]
    url = f"{_base()}/api/permissions/jwks"
    response = client.get(url, headers=_headers())
    response.raise_for_status()
    keys = response.json().get("keys") or []
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return keys


def _verify_assertion(client: httpx.Client, assertion: str, audience: str) -> dict[str, Any]:
    keys = _fetch_jwks(client)
    if not keys:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Superdirectory JWKS unavailable",
        )
    header = jwt.get_unverified_header(assertion)
    kid = header.get("kid")
    candidates = [k for k in keys if not kid or k.get("kid") == kid] or keys
    last_err: Exception | None = None
    for jwk_dict in candidates:
        try:
            key = jwk.construct(jwk_dict)
            return jwt.decode(
                assertion,
                key,
                algorithms=["RS256"],
                audience=audience,
                issuer=settings.REDPAGE_PERMISSIONS_ISSUER,
            )
        except Exception as exc:  # noqa: BLE001 — try next key
            last_err = exc
            continue
    logger.warning("Permission assertion verify failed: %s", last_err)
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Invalid permission assertion from Superdirectory",
    )


def fetch_clubs(client: httpx.Client | None = None) -> list[ClubInfo]:
    owns = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        response = client.get(f"{_base()}/api/clubs", headers=_headers())
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not load clubs from Superdirectory",
            )
        payload = response.json()
        base = _base()
        clubs: list[ClubInfo] = []
        for c in payload:
            logo = c.get("logo_url")
            if not logo:
                # Superdir serves logos at /api/clubs/{id}/logo
                logo = f"{base}/api/clubs/{c['club_id']}/logo"
            elif logo.startswith("/"):
                logo = f"{base}{logo}"
            clubs.append(
                ClubInfo(
                    club_id=c["club_id"],
                    name=c.get("name") or c["club_id"],
                    type=c.get("type"),
                    logo_url=logo,
                    description=c.get("description"),
                )
            )
        return clubs
    finally:
        if owns:
            client.close()


def fetch_club_pors(club_id: str, *, client: httpx.Client | None = None) -> list[dict[str, Any]]:
    """Fetch POR holders for a Superdir club (public clubs API)."""
    owns = client is None
    client = client or httpx.Client(timeout=20.0)
    try:
        response = client.get(
            f"{_base()}/api/clubs/{club_id}/pors",
            headers=_headers(),
        )
        if response.status_code >= 400:
            logger.warning("Superdir club PORs fetch failed for %s: %s", club_id, response.status_code)
            return []
        data = response.json()
        return data if isinstance(data, list) else []
    finally:
        if owns:
            client.close()


def fetch_permissions(kerberos: str, *, audience: str | None = None) -> PermissionsAccess:
    """Fetch universal permissions and verify the RS256 assertion."""
    if not settings.REDPAGE_API_BASE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Superdirectory is not configured (REDPAGE_API_BASE)",
        )
    aud = audience or settings.REDPAGE_PERMISSIONS_AUDIENCE
    login = kerberos.lower().strip()
    url = f"{_base()}/api/permissions/{login}"
    with httpx.Client(timeout=20.0) as client:
        response = client.get(url, params={"audience": aud}, headers=_headers())
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not load permissions from Superdirectory",
            )
        data = response.json()
        assertion = data.get("assertion") or ""
        if assertion and settings.REDPAGE_VERIFY_ASSERTION:
            claims = _verify_assertion(client, assertion, aud)
            # Prefer verified claims for security-sensitive fields
            data["global_level"] = claims.get("global_level")
            data["club_levels"] = claims.get("club_levels") or {}
            data["capabilities"] = claims.get("capabilities") or data.get("capabilities") or {}
            data["kerberos"] = claims.get("sub") or data.get("kerberos")
        clubs = fetch_clubs(client)
        access = PermissionsAccess.model_validate({**data, "clubs": [c.model_dump() for c in clubs]})
        return access


def _short_kerberos_from_entry(entry: str) -> str | None:
    """
    Convert full IITD entry numbers to kerberos-style ids used by Superdir.
    2024MS10098 → ms1240098, 2024CS10020 → cs1240020
    """
    e = entry.upper().strip()
    if len(e) >= 9 and e[:4].isdigit() and e[4:6].isalpha():
        year = e[2:4]  # 24 from 2024
        dept = e[4:6].lower()
        program = e[6] if len(e) > 6 else ""
        rest = e[7:].lower()
        if program and rest:
            return f"{dept}{program}{year}{rest}".lower()
    return None


def user_kerberos_candidates(user) -> list[str]:
    """
    Identifiers to try against Superdir Student.kerberos.

    Prefer email local-part (matches Superdir). Entry numbers are often the
    full 11-char form and will NOT match without conversion.
    """
    candidates: list[str] = []
    email = (getattr(user, "email", None) or "").split("@")[0].lower().strip()
    if email:
        candidates.append(email)

    entry = (getattr(user, "entry_number", None) or "").strip()
    if entry:
        short = _short_kerberos_from_entry(entry)
        if short:
            candidates.append(short)
        candidates.append(entry.lower())

    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def user_kerberos(user) -> str:
    cands = user_kerberos_candidates(user)
    return cands[0] if cands else ""
