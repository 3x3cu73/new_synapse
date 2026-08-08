from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile, Request
from sqlalchemy.orm import Session
from app.api import deps
from app.models.event import Event
from app.models.organization import Organization
from app.models.role import Role
from app.schemas.event import EventOut
from app.core.timezone import now_utc
from datetime import datetime, timedelta, timezone
import json
import re
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Kerberos ID pattern: 2 letters + 1 alphanumeric + 2 digits + 4 digits (e.g. cs1240020)
KERBEROS_PATTERN = re.compile(r"^[a-zA-Z]{2}[a-zA-Z0-9]\d{6}$")

CAIC_ORG_NAME = "Co-Curricular and Academic Interaction Council"


def authenticate_by_kerberos(
    kerberos_id: str,
    db: Session,
) -> Role:
    """
    Authenticate via kerberos ID (entry_number) stored on the User model.
    Validates that the user belongs to the CAIC organization.
    """
    if not KERBEROS_PATTERN.match(kerberos_id):
        raise HTTPException(status_code=400, detail="Invalid kerberos ID format")

    from app.models.user import User

    # Find user by entry number
    user = (
        db.query(User)
        .filter(User.entry_number == kerberos_id.lower())
        .first()
    )
    if not user:
        raise HTTPException(status_code=403, detail="User not found for this kerberos ID.")

    # Find the CAIC organization
    caic_org = db.query(Organization).filter(Organization.name == CAIC_ORG_NAME).first()
    if not caic_org:
        raise HTTPException(status_code=500, detail="CAIC organization not configured.")

    # Check user has a role in CAIC
    role = (
        db.query(Role)
        .filter(Role.user_id == user.id, Role.org_id == caic_org.id)
        .first()
    )
    if not role:
        raise HTTPException(
            status_code=403,
            detail="Not authorized. No CAIC board role found for this kerberos ID.",
        )

    return role


@router.post("/create-event", response_model=EventOut)
@limiter.limit("5/minute")
def create_caic_event(
    request: Request,
    kerberos_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    venue: str = Form(...),
    tags: str = Form("[]"),
    custom_form_schema: str = Form("[]"),
    target_audience: str = Form("{}"),
    is_private: bool = Form(False),
    registration_deadline: str = Form(None),
    event_manager_email: str = Form(...),
    duration_hours: float = Form(None),
    photo: UploadFile = File(None),
    db: Session = Depends(deps.get_db),
):
    # 1. Authenticate via kerberos
    role = authenticate_by_kerberos(kerberos_id, db)

    org = db.query(Organization).filter(Organization.id == role.org_id).first()

    # 2. Handle file upload
    image_url = org.banner_url if org else None
    if photo:
        import uuid
        from app.services.local_uploads import save_upload_file

        result = save_upload_file(
            photo, folder="events", public_id=str(uuid.uuid4())
        )
        image_url = result["secure_url"]

    # 3. Parse & validate fields
    try:
        tags_list = json.loads(tags)
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

    # 4. Create event linked to CAIC org
    event = Event(
        name=name,
        description=description,
        date=date_obj,
        registration_deadline=deadline_obj,
        venue=venue,
        image_url=image_url,
        tags=tags_list,
        custom_form_schema=schema_list,
        target_audience=audience_dict,
        is_private=is_private,
        org_id=role.org_id,
        event_manager_email=event_manager_email,
        duration_hours=duration_hours,
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    return event
