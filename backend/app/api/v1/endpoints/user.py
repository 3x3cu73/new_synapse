from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
from app.schemas.user import UserOut
from app.schemas.event import EventOut
import uuid
from fastapi import Form, File, UploadFile
import json
from app.services.local_uploads import save_upload_file
from app.models.enums import HostelName

from app.models.registration import Registration
from datetime import datetime, timezone
from app.core.timezone import now_utc

router = APIRouter()

@router.put("/profile", response_model=UserOut)
def update_profile(
    hostel: str = Form(None),
    interests: str = Form(None),
    photo: UploadFile = File(None),
    remove_photo: bool = Form(False),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # 🔴 REMOVE PHOTO
    if remove_photo:
        current_user.photo_url = None

    # 🟢 UPLOAD NEW PHOTO
    elif photo:
        result = save_upload_file(
            photo,
            folder="profiles",
            public_id=str(uuid.uuid4()),
        )
        current_user.photo_url = result["secure_url"]

    # User-editable fields
    if hostel is not None:
        try:
            current_user.hostel = HostelName(hostel)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid hostel: '{hostel}'. Must be a valid IITD hostel name.")
    if interests is not None:
        current_user.interests = json.loads(interests)

    db.commit()
    db.refresh(current_user)
    return current_user




@router.get("/calendar", response_model=list[EventOut])
def get_my_calendar(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get all events the user has registered for."""
    # SQLAlchemy relationship magic
    return [reg.event for reg in current_user.registrations]


@router.get("/feedback-pending", response_model=list[EventOut])
def get_feedback_pending(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get past events the user registered for but hasn't rated yet."""
    now = now_utc()

    pending = (
        db.query(Registration)
        .filter(
            Registration.user_id == current_user.id,
            Registration.feedback_rating.is_(None)
        )
        .all()
    )

    # Only show events whose date has already passed
    result = []
    for reg in pending:
        event_date = reg.event.date
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
        if event_date < now:
            result.append(reg.event)

    return result
