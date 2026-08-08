from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrganizationCreate(BaseModel):
    name: str
    org_type: str
    banner_url: Optional[str] = None
    genres: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    org_type: Optional[str] = None
    banner_url: Optional[str] = None
    genres: Optional[str] = None


class OrganizationOut(BaseModel):
    id: int
    name: str
    org_type: str
    banner_url: Optional[str] = None
    genres: Optional[str] = None
    external_club_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
