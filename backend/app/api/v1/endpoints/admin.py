from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, subqueryload
from sqlalchemy import func
import secrets, hashlib
from app.api import deps
from app.models.user import User
from app.models.organization import Organization
from app.models.role import Role
from app.models.event import Event
from app.models.registration import Registration
from app.models.api_key import ApiKey
from app.schemas.user import RoleCreate, UserOut, UserListResponse
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationOut

router = APIRouter()


def get_superuser(current_user: User = Depends(deps.get_current_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not a Superuser")
    return current_user


# ------------------------------------------------------------------
# ORG CRUD (Superuser only)
# ------------------------------------------------------------------
@router.get("/orgs", response_model=list[OrganizationOut])
def list_organizations(
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    return db.query(Organization).order_by(Organization.name).all()


@router.post("/orgs", response_model=OrganizationOut)
def create_organization(
    org_in: OrganizationCreate,
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    existing = db.query(Organization).filter(Organization.name == org_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization already exists")
    org = Organization(name=org_in.name, org_type=org_in.org_type)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.put("/orgs/{org_id}", response_model=OrganizationOut)
def update_organization(
    org_id: int,
    org_in: OrganizationUpdate,
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org_in.name is not None:
        org.name = org_in.name
    if org_in.org_type is not None:
        org.org_type = org_in.org_type
    db.commit()
    db.refresh(org)
    return org


@router.delete("/orgs/{org_id}", status_code=204)
def delete_organization(
    org_id: int,
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    # Clubs synced from Superdirectory are owned by Superdir PORs — never
    # deletable from Synapse (a coordinator / CAIC admin must not wipe other clubs).
    if org.external_club_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot delete a Superdirectory club from Synapse. "
            "Remove or edit it in Superdirectory instead.",
        )
    db.delete(org)
    db.commit()


# ------------------------------------------------------------------
# ROLE / AUTHORIZATION
# ------------------------------------------------------------------
@router.post("/authorize")
def authorize_club_head(
    email: str,
    role_data: RoleCreate,
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    """Give a student the power to manage a Club/Fest."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    org = db.query(Organization).filter(Organization.id == role_data.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    role_name_val = role_data.role_name.value if hasattr(role_data.role_name, 'value') else role_data.role_name

    existing = db.query(Role).filter(
        Role.user_id == user.id,
        Role.org_id == role_data.org_id,
        Role.role_name == role_name_val,
    ).first()
    if existing:
        return {"msg": "User already has this role"}

    new_role = Role(
        user_id=user.id,
        org_id=role_data.org_id,
        role_name=role_name_val,
    )
    db.add(new_role)
    db.commit()
    return {"msg": f"Authorized {user.name} for {org.name} as {role_name_val}"}


@router.delete("/revoke")
def revoke_role(
    email: str,
    org_id: int,
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = db.query(Role).filter(Role.user_id == user.id, Role.org_id == org_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
    return {"msg": "Role revoked"}


# ------------------------------------------------------------------
# USER MANAGEMENT
# ------------------------------------------------------------------
@router.get("/users", response_model=UserListResponse)
def list_all_users(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    total = db.query(func.count(User.id)).scalar()
    user_ids = [
        uid for (uid,) in
        db.query(User.id).order_by(User.id).offset(skip).limit(limit).all()
    ]
    users = (
        db.query(User)
        .options(joinedload(User.roles).joinedload(Role.organization))
        .filter(User.id.in_(user_ids))
        .order_by(User.id)
        .all()
    ) if user_ids else []
    return {"users": users, "total": total}


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser:
        raise HTTPException(status_code=403, detail="Cannot delete another superuser")
    db.delete(user)
    db.commit()


# ------------------------------------------------------------------
# ORG ANALYTICS (Superuser: view any org, but NO event editing)
# ------------------------------------------------------------------
@router.get("/orgs/{org_id}/analytics")
def get_org_analytics(
    org_id: int,
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Use aggregate queries instead of loading all registrations into Python
    total_events = db.query(func.count(Event.id)).filter(Event.org_id == org_id).scalar()
    total_regs = (
        db.query(func.count(Registration.id))
        .join(Event, Registration.event_id == Event.id)
        .filter(Event.org_id == org_id)
        .scalar()
    )

    # Dept analytics via SQL aggregation
    dept_rows = (
        db.query(User.department, func.count(Registration.id))
        .join(Registration, Registration.user_id == User.id)
        .join(Event, Registration.event_id == Event.id)
        .filter(Event.org_id == org_id)
        .group_by(User.department)
        .all()
    )
    dept_counts = {}
    for dept, count in dept_rows:
        dept_key = (dept.value if hasattr(dept, 'value') else dept) or "Unknown"
        dept_counts[dept_key] = count

    # Team members with eager-loaded user
    team = db.query(Role).options(joinedload(Role.user)).filter(Role.org_id == org_id).all()

    return {
        "org_id": org.id,
        "org_name": org.name,
        "org_type": org.org_type,
        "org_banner": org.banner_url,
        "total_events": total_events,
        "total_registrations": total_regs,
        "dept_analytics": dept_counts,
        "team": [{"user_id": r.user_id, "name": r.user.name, "email": r.user.email, "role": r.role_name} for r in team],
    }


# ------------------------------------------------------------------
# API KEY MANAGEMENT (Superuser only)
# ------------------------------------------------------------------
@router.post("/orgs/{org_id}/api-keys")
def generate_org_api_key(
    org_id: int,
    db: Session = Depends(deps.get_db),
    admin: User = Depends(get_superuser),
):
    """Generate a new API key for the org. Revokes any existing active keys first."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Revoke all existing active keys for this org
    db.query(ApiKey).filter(ApiKey.org_id == org_id, ApiKey.is_active == True).update(
        {"is_active": False}
    )

    raw_key = f"syn_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        org_id=org_id,
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        label="default",
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": api_key.id,
        "org_id": org_id,
        "key": raw_key,
        "key_prefix": api_key.key_prefix,
        "msg": "Store this key securely. It will NOT be shown again.",
    }
    db.commit()
    return {"msg": "API key revoked"}
