from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Response, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional
from app.api import deps
from app.models.user import User
from app.models.event import Event
from app.models.organization import Organization
from app.models.role import Role
from app.models.registration import Registration
from app.models.api_key import ApiKey
from app.models.event_request import EventRequest
from app.schemas.event import EventOut
from app.schemas.user import TeamMemberCreate
from app.schemas.organization import OrganizationOut
from app.services.exports import generate_event_registration_csv
import json
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from app.core.timezone import now_utc
from app.services.local_uploads import save_upload_file
import uuid
from app.services.sqs import send_event, SQSEvent, EventType
from app.models.notification import Notification
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ------------------------------------------------------------------
# HIERARCHY DEFINITIONS
# ------------------------------------------------------------------
HEAD_ROLES_SET = {
    "overall coordinator",
    "co overall coordinator",
    "caic admin",
    "president",
    "vice president",
    "general secretary",
    "deputy general secretary",
    "secretary",
    "convener"
}

# Access-only label — not a club team membership.
CAIC_ADMIN_ROLE = "caic admin"


# ------------------------------------------------------------------
# DEPENDENCIES
# ------------------------------------------------------------------
def get_org_role(
    org_id: int,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    """
    Validates org management access.

    Prefer Superdirectory universal capability `manage_events` (coordinator+),
    syncing roles into Synapse. Falls back to a local Role row for non-CAIC orgs.
    """
    from app.services.superdir_sync import (
        can_manage_events_for_org,
        sync_user_from_superdir,
    )

    access = None
    try:
        access = sync_user_from_superdir(db, current_user)
    except Exception:
        access = None

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    role = db.query(Role).filter(
        Role.user_id == current_user.id,
        Role.org_id == org_id,
    ).first()

    # Synapse platform superuser — full org access.
    if current_user.is_superuser:
        if role:
            return role
        label = (
            CAIC_ADMIN_ROLE
            if access and access.is_superadmin
            else "overall coordinator"
        )
        return Role(user_id=current_user.id, org_id=org_id, role_name=label)

    # Superdir CAIC admin (global_level=0) — full access to Superdir clubs.
    # Keep real POR title when present; otherwise label as caic admin.
    if access and access.is_superadmin and org.external_club_id:
        return role or Role(
            user_id=current_user.id, org_id=org_id, role_name=CAIC_ADMIN_ROLE
        )

    # Superdir-linked clubs: POR / manage_events.
    if org.external_club_id:
        if access and can_manage_events_for_org(access, org):
            if role:
                return role
            role = db.query(Role).filter(
                Role.user_id == current_user.id,
                Role.org_id == org_id,
            ).first()
            if role:
                return role
            raise HTTPException(
                status_code=403,
                detail="Superdirectory granted manage_events but Synapse role sync failed.",
            )
        if role:
            return role
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to manage this organization. "
            "Club coordinators+ are granted via Superdirectory PORs.",
        )

    # Local / non-Superdir orgs
    if role:
        return role

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to manage this organization.",
    )


def get_org_head(
    role: Role = Depends(get_org_role)
):
    """Validates that the requester is a HEAD (e.g., President, OC)."""
    if role.role_name not in HEAD_ROLES_SET:
        raise HTTPException(status_code=403, detail="Permission Denied. Only Organization Heads can manage the team.")
    return role


# ------------------------------------------------------------------
# DASHBOARD & ANALYTICS
# ------------------------------------------------------------------
@router.get("/{org_id}/dashboard")
def get_org_dashboard(
    org_id: int,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Use SQL aggregation instead of loading all registrations into Python
    total_events = db.query(func.count(Event.id)).filter(Event.org_id == org_id).scalar()
    total_regs = (
        db.query(func.count(Registration.id))
        .join(Event, Registration.event_id == Event.id)
        .filter(Event.org_id == org_id)
        .scalar()
    )

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

    return {
        "org_id": org.id,
        "org_name": org.name,
        "org_type": org.org_type,
        "org_banner": org.banner_url,
        "org_genres": org.genres,
        "your_role": role.role_name,
        "total_events": total_events,
        "total_registrations": total_regs,
        "dept_analytics": dept_counts
    }


# ------------------------------------------------------------------
# EVENT MANAGEMENT
# ------------------------------------------------------------------
@router.get("/{org_id}/events", response_model=list[EventOut])
def get_org_events(
    org_id: int,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    return (
        db.query(Event)
        .options(joinedload(Event.organization))
        .filter(Event.org_id == org_id)
        .order_by(Event.date.desc())
        .all()
    )


@router.post("/{org_id}/events", response_model=EventOut)
def create_org_event(
    org_id: int,
    name: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    venue: str = Form(...),
    tags: str = Form("[]"),
    genres: str = Form("[]"),
    custom_form_schema: str = Form("[]"),
    target_audience: str = Form("{}"),
    is_private: bool = Form(False),
    registration_deadline: str = Form(None),
    duration_hours: float = Form(None),
    capacity: int = Form(None),
    request_only: bool = Form(False),
    photo: UploadFile = File(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    role: Role = Depends(get_org_role)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Handle File Upload
    image_url = org.banner_url
    if photo:
        result = save_upload_file(
            photo, folder="events", public_id=str(uuid.uuid4())
        )
        image_url = result["secure_url"]

    # Parse JSON fields
    try:
        tags_list = json.loads(tags)
        genres_list = json.loads(genres)
        schema_list = json.loads(custom_form_schema)
        audience_dict = json.loads(target_audience)

        date_obj = datetime.fromisoformat(date)
        if date_obj.tzinfo is None:
            date_obj = date_obj.replace(tzinfo=timezone.utc)

        now = now_utc()

        if date_obj <= now:
            raise HTTPException(status_code=400, detail="Event date must be in the future")
        if date_obj < now + timedelta(minutes=5):
            raise HTTPException(status_code=400, detail="Event must be scheduled at least 5 minutes in advance")
        if date_obj > now + timedelta(days=365):
            raise HTTPException(status_code=400, detail="Event date cannot be more than 1 year in the future")

        deadline_obj = None
        if registration_deadline:
            deadline_obj = datetime.fromisoformat(registration_deadline)
            if deadline_obj.tzinfo is None:
                deadline_obj = deadline_obj.replace(tzinfo=timezone.utc)
            if deadline_obj <= now:
                raise HTTPException(status_code=400, detail="Registration deadline must be in the future")
            if deadline_obj >= date_obj:
                raise HTTPException(status_code=400, detail="Registration deadline must be before the event date")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in request")

    event = Event(
        name=name,
        description=description,
        date=date_obj,
        registration_deadline=deadline_obj,
        venue=venue,
        image_url=image_url,
        tags=tags_list,
        genres=genres_list,
        custom_form_schema=schema_list,
        target_audience=audience_dict,
        is_private=is_private,
        org_id=org_id,
        event_manager_email=current_user.email,
        duration_hours=duration_hours,
        capacity=capacity,
        request_only=request_only,
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/{org_id}/events/{event_id}", status_code=204)
def delete_event(
    org_id: int,
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    role: Role = Depends(get_org_role)
):
    event = db.query(Event).filter(Event.id == event_id, Event.org_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()


@router.put("/{org_id}/events/{event_id}", response_model=EventOut)
def update_event(
    org_id: int,
    event_id: int,
    name: str = Form(None),
    description: str = Form(None),
    date: str = Form(None),
    venue: str = Form(None),
    tags: str = Form(None),
    genres: str = Form(None),
    custom_form_schema: str = Form(None),
    target_audience: str = Form(None),
    is_private: bool = Form(None),
    registration_deadline: str = Form(None),
    capacity: int = Form(None),
    request_only: bool = Form(None),
    photo: UploadFile = File(None),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    role: Role = Depends(get_org_role)
):
    event = db.query(Event).options(joinedload(Event.organization)).filter(
        Event.id == event_id, Event.org_id == org_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if photo and photo.filename:
        result = save_upload_file(
            photo, folder="events", public_id=str(uuid.uuid4())
        )
        event.image_url = result["secure_url"]

    if date:
        try:
            date_obj = datetime.fromisoformat(date)
            if date_obj.tzinfo is None:
                date_obj = date_obj.replace(tzinfo=timezone.utc)
            now = now_utc()
            if date_obj <= now:
                raise HTTPException(status_code=400, detail="Event date must be in the future")
            if date_obj < now + timedelta(minutes=5):
                raise HTTPException(status_code=400, detail="Event must be scheduled at least 5 minutes in advance")
            if date_obj > now + timedelta(days=365):
                raise HTTPException(status_code=400, detail="Event date cannot be more than 1 year in the future")
            event.date = date_obj
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    if name is not None:
        event.name = name
    if description is not None:
        event.description = description
    if venue is not None:
        event.venue = venue
    if is_private is not None:
        event.is_private = is_private

    if registration_deadline is not None:
        if registration_deadline == "":
            event.registration_deadline = None
        else:
            try:
                dl_obj = datetime.fromisoformat(registration_deadline)
                if dl_obj.tzinfo is None:
                    dl_obj = dl_obj.replace(tzinfo=timezone.utc)
                now = now_utc()
                event_date = event.date if event.date.tzinfo else event.date.replace(tzinfo=timezone.utc)
                if dl_obj <= now:
                    raise HTTPException(status_code=400, detail="Registration deadline must be in the future")
                if dl_obj >= event_date:
                    raise HTTPException(status_code=400, detail="Registration deadline must be before the event date")
                event.registration_deadline = dl_obj
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format for registration_deadline")

    if tags:
        event.tags = json.loads(tags)
    if genres:
        event.genres = json.loads(genres)
    if custom_form_schema:
        event.custom_form_schema = json.loads(custom_form_schema)
    if target_audience:
        event.target_audience = json.loads(target_audience)
    if capacity is not None:
        event.capacity = capacity if capacity > 0 else None
    if request_only is not None:
        event.request_only = request_only

    db.commit()
    db.refresh(event)
    return event


# ------------------------------------------------------------------
# DATA EXPORTS & REGISTRATIONS
# ------------------------------------------------------------------
@router.get("/{org_id}/events/{event_id}/registrations")
def get_event_registrations(
    org_id: int,
    event_id: int,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    event = db.query(Event).filter(Event.id == event_id, Event.org_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found or not owned by you")

    regs = (
        db.query(Registration)
        .options(joinedload(Registration.user))
        .filter(Registration.event_id == event_id)
        .all()
    )

    return [{
        "name": reg.user.name,
        "email": reg.user.email,
        "entry_number": reg.user.entry_number,
        "department": reg.user.department.value if hasattr(reg.user.department, 'value') else reg.user.department,
        "hostel": reg.user.hostel.value if hasattr(reg.user.hostel, 'value') else reg.user.hostel,
        "photo_url": reg.user.photo_url,
        "registered_at": reg.registered_at,
    } for reg in regs]


@router.get("/{org_id}/events/{event_id}/csv")
def download_event_csv(
    org_id: int,
    event_id: int,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    event = db.query(Event).filter(Event.id == event_id, Event.org_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    csv_file = generate_event_registration_csv(db, event_id)

    return Response(
        content=csv_file.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=registrations_{event_id}.csv"}
    )


@router.get("/{org_id}/events/{event_id}/feedback")
def get_event_feedback(
    org_id: int,
    event_id: int,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    event = db.query(Event).filter(Event.id == event_id, Event.org_id == org_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    ratings = [r.feedback_rating for r in event.registrations if r.feedback_rating]

    if not ratings:
        return {"average": 0, "count": 0, "distribution": {}}

    return {
        "average": round(sum(ratings) / len(ratings), 1),
        "count": len(ratings),
        "distribution": {i: ratings.count(i) for i in range(1, 11)}
    }


# ------------------------------------------------------------------
# EVENT REQUESTS MANAGEMENT
# ------------------------------------------------------------------
@router.get("/{org_id}/requests")
def get_org_requests(
    org_id: int,
    status: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    """List all event requests for this org. Optional ?status=0 for pending only."""
    query = (
        db.query(EventRequest)
        .options(joinedload(EventRequest.user), joinedload(EventRequest.event))
        .filter(EventRequest.org_id == org_id)
    )
    if status is not None:
        query = query.filter(EventRequest.status == status)
    requests = query.order_by(EventRequest.created_at.desc()).all()

    return [{
        "id": r.id,
        "event_id": r.event_id,
        "event_name": r.event.name,
        "event_date": r.event.date,
        "user_id": r.user_id,
        "user_name": r.user.name,
        "user_email": r.user.email,
        "user_entry_number": r.user.entry_number,
        "user_department": r.user.department.value if hasattr(r.user.department, 'value') else r.user.department,
        "user_photo_url": r.user.photo_url,
        "status": r.status,
        "form_response": r.form_response,
        "created_at": r.created_at,
    } for r in requests]


@router.patch("/{org_id}/requests/{request_id}")
def handle_event_request(
    org_id: int,
    request_id: str,
    body: dict,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    """Accept (status=1) or reject (status=-1) a request."""
    new_status = body.get("status")
    if new_status not in (1, -1):
        raise HTTPException(status_code=400, detail="status must be 1 (accept) or -1 (reject)")

    req = db.query(EventRequest).filter(
        EventRequest.id == request_id, EventRequest.org_id == org_id
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Store info before deleting
    req_user_id = req.user_id
    req_event_id = req.event_id
    msg = "rejected"

    # If accepted, auto-register the user
    if new_status == 1:
        event = db.query(Event).filter(Event.id == req_event_id).first()
        if event and event.capacity is not None:
            current_count = db.query(func.count(Registration.id)).filter(Registration.event_id == req_event_id).scalar()
            if current_count >= event.capacity:
                db.delete(req)
                db.commit()
                # Still notify the user their request was approved (but full)
                try:
                    event_date_str = event.date.strftime('%d %b %Y, %I:%M %p') if event.date else ''
                    full_title = f"Request approved for {event.name}"
                    full_body = f"Your request to join {event.name} on {event_date_str} at {event.venue} has been approved, but the event is currently full."
                    db.add(Notification(user_id=req_user_id, title=full_title, body=full_body))
                    db.commit()
                    send_event(SQSEvent(
                        type=EventType.NOTIFICATION,
                        to=[str(req_user_id)],
                        title=full_title,
                        body=full_body,
                    ))
                except Exception as e:
                    logger.warning(f"Failed to send request action notification: {e}")
                return {"status": "accepted", "msg": "Request accepted but event is full. User was not auto-registered."}

        existing = db.query(Registration).filter(
            Registration.user_id == req_user_id, Registration.event_id == req_event_id
        ).first()
        if not existing:
            db.add(Registration(user_id=req_user_id, event_id=req_event_id, custom_answers={}))
        msg = "accepted"

    # Delete the request entry
    db.delete(req)
    db.commit()

    # Notify the requester
    try:
        event = db.query(Event).filter(Event.id == req_event_id).first() if new_status != 1 else event
        if event:
            event_date_str = event.date.strftime('%d %b %Y, %I:%M %p') if event.date else ''
            action_word = "approved" if new_status == 1 else "declined"
            title = f"Request {action_word} for {event.name}"
            body = f"Your request to join {event.name} on {event_date_str} at {event.venue} has been {action_word}."

            # Persist in-app notification
            db.add(Notification(user_id=req_user_id, title=title, body=body))
            db.commit()

            # Push to SQS
            send_event(SQSEvent(
                type=EventType.NOTIFICATION,
                to=[str(req_user_id)],
                title=title,
                body=body,
            ))
    except Exception as e:
        logger.warning(f"Failed to send request action notification: {e}")

    return {"status": "success", "msg": f"Request {msg}"}


# ------------------------------------------------------------------
# TEAM MANAGEMENT
# ------------------------------------------------------------------
_SUPERDIR_ROLE_LABELS = {
    "oc": "overall coordinator",
    "co_oc": "co overall coordinator",
    "coordinator": "coordinator",
    "panel_member": "panel member",
    "executive": "executive",
}


@router.get("/{org_id}/team")
def get_team_members(
    org_id: int,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    """
    Team list for an org.

    Superdir-linked clubs: show all current-year PORs from Superdirectory
    (not only people who have logged into Synapse). Local Synapse-only
    roles are appended if missing.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    team_roles = (
        db.query(Role)
        .options(joinedload(Role.user))
        .filter(Role.org_id == org_id)
        .all()
    )
    local_by_email = {
        (r.user.email or "").lower(): r for r in team_roles if r.user and r.user.email
    }
    local_by_kerberos = {}
    for r in team_roles:
        if not r.user:
            continue
        for key in (
            (r.user.email or "").split("@")[0].lower(),
            (r.user.entry_number or "").lower(),
        ):
            if key:
                local_by_kerberos[key] = r

    members: list[dict] = []
    seen_emails: set[str] = set()
    seen_kerberos: set[str] = set()

    if org.external_club_id:
        from app.services.redpage_permissions import fetch_club_pors

        try:
            pors = fetch_club_pors(org.external_club_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load Superdir PORs for %s: %s", org.external_club_id, exc)
            pors = []

        if pors:
            years = [p.get("academic_year") for p in pors if p.get("academic_year")]
            current_year = max(years) if years else None
            if current_year:
                pors = [p for p in pors if p.get("academic_year") == current_year]

        role_rank = {"oc": 0, "co_oc": 1, "coordinator": 2, "panel_member": 3, "executive": 4}
        pors.sort(key=lambda p: (role_rank.get(str(p.get("role")), 9), (p.get("name") or "").lower()))

        for por in pors:
            kerberos = (por.get("kerberos") or "").lower()
            email = (por.get("email") or "").lower() or (f"{kerberos}@iitd.ac.in" if kerberos else "")
            local = local_by_kerberos.get(kerberos) or local_by_email.get(email)
            label = _SUPERDIR_ROLE_LABELS.get(str(por.get("role")), str(por.get("role") or "member"))
            members.append({
                "user_id": local.user_id if local else None,
                "kerberos": kerberos,
                "name": por.get("name") or kerberos,
                "email": (local.user.email if local and local.user else email),
                "role": label,
                "photo_url": local.user.photo_url if local and local.user else None,
                "source": "superdir",
            })
            if email:
                seen_emails.add(email)
            if kerberos:
                seen_kerberos.add(kerberos)

    # Superdir-linked clubs: roster is read-only from RedPage PORs only.
    if org.external_club_id:
        return members

    for r in team_roles:
        role_l = (r.role_name or "").lower()
        email = (r.user.email or "").lower() if r.user else ""
        kerberos = (
            (r.user.entry_number or "").lower()
            if r.user and getattr(r.user, "entry_number", None)
            else (email.split("@")[0] if email else "")
        )
        if email in seen_emails or kerberos in seen_kerberos:
            continue
        if role_l in {CAIC_ADMIN_ROLE, "overall coordinator", "co overall coordinator"}:
            continue
        members.append({
            "user_id": r.user_id,
            "kerberos": kerberos,
            "name": r.user.name if r.user else "Unknown",
            "email": r.user.email if r.user else "",
            "role": r.role_name,
            "photo_url": r.user.photo_url if r.user else None,
            "source": "synapse",
        })

    return members


@router.post("/{org_id}/team")
def add_team_member(
    org_id: int,
    member_in: TeamMemberCreate,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role),
):
    raise HTTPException(status_code=403, detail="Manage team in Superdirectory.")


@router.delete("/{org_id}/team/{user_id}")
def remove_team_member(
    org_id: int,
    user_id: int,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role),
):
    raise HTTPException(status_code=403, detail="Manage team in Superdirectory.")


@router.post("/{org_id}/banner")
def upload_org_banner(
    org_id: int,
    banner: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    if banner.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only JPG/PNG allowed")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_file_name = org.name.lower().replace(" ", "_")

    result = save_upload_file(
        banner, folder="org_banners", public_id=org_file_name
    )

    org.banner_url = result["secure_url"]
    db.commit()
    db.refresh(org)
    return {"banner_url": result["secure_url"]}


@router.delete("/{org_id}/banner")
def delete_org_banner(
    org_id: int,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Empty string = intentionally cleared (Superdir sync must not restore logo).
    org.banner_url = ""
    db.commit()
    return {"banner_url": "", "msg": "Banner removed"}


@router.patch("/{org_id}/genres")
def update_org_genres(
    org_id: int,
    body: dict,
    db: Session = Depends(deps.get_db),
    role: Role = Depends(get_org_role)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    genres_list = body.get("genres", [])
    if not isinstance(genres_list, list):
        raise HTTPException(status_code=400, detail="genres must be a list")
    org.genres = ",".join(g.strip() for g in genres_list if g.strip())
    db.commit()
    db.refresh(org)
    return {"genres": org.genres}


# ------------------------------------------------------------------
# API KEY MANAGEMENT (HEAD only)
# ------------------------------------------------------------------
@router.get("/{org_id}/api-keys")
def list_api_keys(
    org_id: int,
    db: Session = Depends(deps.get_db),
    head_role: Role = Depends(get_org_head),
):
    keys = db.query(ApiKey).filter(ApiKey.org_id == org_id).order_by(ApiKey.created_at.desc()).all()
    return [{
        "id": k.id,
        "key_prefix": k.key_prefix,
        "label": k.label,
        "is_active": k.is_active,
        "allowed_ips": k.allowed_ips,
        "created_at": k.created_at,
        "last_used_at": k.last_used_at,
    } for k in keys]


@router.post("/{org_id}/api-keys")
def create_api_key(
    org_id: int,
    payload: dict = None,
    db: Session = Depends(deps.get_db),
    head_role: Role = Depends(get_org_head),
):
    """Generate a new API key for the org. Returns the raw key ONCE."""
    label = (payload or {}).get("label", "default")
    allowed_ips = (payload or {}).get("allowed_ips", [])

    # Validate IPs if provided
    if not isinstance(allowed_ips, list):
        raise HTTPException(status_code=400, detail="allowed_ips must be a list")

    raw_key = f"syn_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        org_id=org_id,
        key_hash=key_hash,
        key_prefix=raw_key[:8],
        label=label,
        allowed_ips=allowed_ips,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": api_key.id,
        "key": raw_key,  # shown ONCE, never stored in plaintext
        "key_prefix": api_key.key_prefix,
        "label": api_key.label,
        "allowed_ips": api_key.allowed_ips,
        "msg": "Store this key securely. It will NOT be shown again.",
    }


@router.delete("/{org_id}/api-keys/{key_id}")
def revoke_api_key(
    org_id: int,
    key_id: int,
    db: Session = Depends(deps.get_db),
    head_role: Role = Depends(get_org_head),
):
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.org_id == org_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()
    return {"msg": "API key revoked"}
