"""Sync Superdirectory clubs + manage_events capabilities into Synapse."""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.role import Role
from app.models.user import User
from app.services.redpage_permissions import (
    ClubInfo,
    PermissionsAccess,
    fetch_permissions,
)

logger = logging.getLogger(__name__)

MANAGE_EVENTS_MAX_LEVEL = 3

LEVEL_TO_ROLE = {
    0: "overall coordinator",
    1: "overall coordinator",
    2: "overall coordinator",
    3: "coordinator",
}

# Synthetic access label for Superdir CAIC admins on clubs without a POR.
CAIC_ADMIN_ROLE = "caic admin"

CLUB_TYPE_TO_ORG_TYPE = {
    "technical_club": "club",
    "department_society": "society",
}

SUPERDIR_MANAGED_ROLES = set(LEVEL_TO_ROLE.values()) | {CAIC_ADMIN_ROLE}

_schema_ready = False


def ensure_org_schema(db: Session) -> None:
    """Add external_club_id if missing (idempotent)."""
    global _schema_ready
    if _schema_ready:
        return
    try:
        db.execute(
            text(
                "ALTER TABLE organizations "
                "ADD COLUMN IF NOT EXISTS external_club_id VARCHAR"
            )
        )
        db.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_organizations_external_club_id "
                "ON organizations (external_club_id)"
            )
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("ensure_org_schema: %s", exc)
    _schema_ready = True


def _role_for_level(level: int | None) -> str:
    if level is None:
        return "coordinator"
    return LEVEL_TO_ROLE.get(level, "coordinator")


def _find_org(db: Session, club_id: str, display_name: str) -> Organization | None:
    org = (
        db.query(Organization)
        .filter(Organization.external_club_id == club_id)
        .first()
    )
    if org:
        return org
    # Legacy rows used club_id as name
    org = db.query(Organization).filter(Organization.name == club_id).first()
    if org:
        return org
    # Already renamed to display name
    if display_name and display_name != club_id:
        org = db.query(Organization).filter(Organization.name == display_name).first()
        if org:
            return org
    return None


def upsert_club(db: Session, club: ClubInfo) -> Organization:
    """Create/update a Synapse organization from a Superdir club (proper name + logo)."""
    display = (club.name or club.club_id).strip()
    org_type = CLUB_TYPE_TO_ORG_TYPE.get(club.type or "", "club")
    org = _find_org(db, club.club_id, display)

    if not org:
        # Avoid unique name collisions
        name = display
        if db.query(Organization).filter(Organization.name == name).first():
            name = f"{display} ({club.club_id})"
        org = Organization(
            name=name,
            external_club_id=club.club_id,
            org_type=org_type,
            banner_url=club.logo_url,
        )
        db.add(org)
        db.flush()
        return org

    changed = False
    if org.external_club_id != club.club_id:
        org.external_club_id = club.club_id
        changed = True
    # Keep display name in sync with Superdir
    if display and org.name != display:
        clash = (
            db.query(Organization)
            .filter(Organization.name == display, Organization.id != org.id)
            .first()
        )
        if not clash:
            org.name = display
            changed = True
    if org.org_type != org_type:
        org.org_type = org_type
        changed = True
    # Logo is Synapse-managed after first set. None = never set → fill from Superdir.
    # "" = intentionally cleared in Synapse; non-empty = custom/upload — do not overwrite.
    if org.banner_url is None and club.logo_url:
        org.banner_url = club.logo_url
        changed = True
    if changed:
        db.flush()
    return org


def sync_all_clubs(db: Session, clubs: list[ClubInfo]) -> list[Organization]:
    """Upsert every Superdir club into Synapse organizations."""
    ensure_org_schema(db)
    orgs = [upsert_club(db, club) for club in clubs]
    db.commit()
    logger.info("Synced %d clubs from Superdir", len(orgs))
    return orgs


def _por_manageable_club_ids(access: PermissionsAccess) -> list[str]:
    return [
        club_id
        for club_id, level in access.club_levels.items()
        if level <= MANAGE_EVENTS_MAX_LEVEL
    ]


def sync_manage_events_roles(db: Session, user: User, access: PermissionsAccess) -> list[Role]:
    """
    1) Sync ALL Superdir clubs (names, logos, types) into the org catalog
    2) Attach manage roles:
       - Synapse platform superuser OR Superdir CAIC admin (global_level=0) → every club
       - Everyone else → POR / manage_events club_ids only

    Does not set Synapse is_superuser from CAIC admin (Admin Panel stays separate).
    Superdir-synced clubs remain non-deletable via Admin API.
    """
    ensure_org_schema(db)
    sync_all_clubs(db, access.clubs)

    clubs_by_id = {c.club_id: c for c in access.clubs}
    # CAIC admin (Redpage/Superdir) and Synapse platform admin see all clubs.
    sees_all = bool(user.is_superuser or access.is_superadmin)
    if sees_all:
        target_ids = [c.club_id for c in access.clubs]
    else:
        cap = access.capability("manage_events")
        if cap.allowed and not cap.all_clubs and cap.club_ids:
            target_ids = [cid for cid in cap.club_ids if cid != "*"]
        else:
            target_ids = _por_manageable_club_ids(access)

    synced: list[Role] = []
    target_org_ids: set[int] = set()

    for club_id in target_ids:
        info = clubs_by_id.get(club_id) or ClubInfo(club_id=club_id, name=club_id)
        org = upsert_club(db, info)
        target_org_ids.add(org.id)
        # Prefer real Superdir POR title. CAIC admin without a POR → "caic admin"
        # (not overall coordinator). Synapse-only superuser → OC.
        level = access.club_levels.get(club_id)
        if level is not None:
            role_name = _role_for_level(level)
        elif access.is_superadmin:
            role_name = CAIC_ADMIN_ROLE
        elif user.is_superuser:
            role_name = "overall coordinator"
        else:
            role_name = _role_for_level(level)

        role = (
            db.query(Role)
            .filter(Role.user_id == user.id, Role.org_id == org.id)
            .first()
        )
        if not role:
            role = Role(user_id=user.id, org_id=org.id, role_name=role_name)
            db.add(role)
            db.flush()
        elif (
            role.role_name in SUPERDIR_MANAGED_ROLES
            or role.role_name == "overall coordinator"
        ) and role.role_name != role_name:
            # Migrate stale OC labels for CAIC admins → caic admin
            role.role_name = role_name
        synced.append(role)

    existing = (
        db.query(Role)
        .filter(Role.user_id == user.id, Role.role_name.in_(SUPERDIR_MANAGED_ROLES))
        .all()
    )
    for role in existing:
        if role.org_id not in target_org_ids:
            db.delete(role)

    db.commit()
    db.refresh(user)
    logger.info(
        "Synced Superdir for %s: clubs=%s role_names=%s superuser=%s",
        user.email,
        [
            (clubs_by_id.get(cid).name if clubs_by_id.get(cid) else cid)
            for cid in target_ids
        ],
        [r.role_name for r in synced],
        user.is_superuser or access.is_superadmin,
    )
    return synced


def sync_user_from_superdir(db: Session, user: User) -> PermissionsAccess | None:
    from app.services.redpage_permissions import user_kerberos_candidates

    candidates = user_kerberos_candidates(user)
    if not candidates:
        return None

    access: PermissionsAccess | None = None
    last_err: Exception | None = None
    for kerberos in candidates:
        try:
            candidate = fetch_permissions(kerberos)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("Superdir permission fetch failed for %s: %s", kerberos, exc)
            continue
        if (
            candidate.global_level is not None
            or candidate.club_levels
            or candidate.capability("manage_events").allowed
            or candidate.capability("manage_events").all_clubs
        ):
            access = candidate
            logger.info(
                "Superdir permissions matched user=%s via kerberos=%s clubs=%s",
                user.email,
                kerberos,
                list(candidate.club_levels.keys()),
            )
            break
        if access is None:
            access = candidate

    if access is None:
        if last_err:
            logger.warning("Superdir permission sync failed for %s: %s", user.email, last_err)
        return None

    sync_manage_events_roles(db, user, access)
    return access


def can_manage_events_for_org(access: PermissionsAccess, org: Organization) -> bool:
    """CAIC admin (global_level=0) may manage every club; others are POR-scoped."""
    if access.is_superadmin:
        return True

    club_id = org.external_club_id or org.name
    cap = access.capability("manage_events")
    if cap.allowed and not cap.all_clubs:
        if club_id in cap.club_ids:
            return True
        name = (org.name or "").strip().lower()
        for club in access.clubs:
            if club.club_id in cap.club_ids and (
                club.name.strip().lower() == name or club.club_id == org.external_club_id
            ):
                return True

    level = access.club_levels.get(club_id)
    if level is not None and level <= MANAGE_EVENTS_MAX_LEVEL:
        return True

    # Match by display name against POR club_levels
    name = (org.name or "").strip().lower()
    for club in access.clubs:
        if club.name.strip().lower() == name or club.club_id == org.external_club_id:
            club_level = access.club_levels.get(club.club_id)
            if club_level is not None and club_level <= MANAGE_EVENTS_MAX_LEVEL:
                return True

    return False
