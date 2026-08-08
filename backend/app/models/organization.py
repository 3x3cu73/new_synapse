from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    # Display name from Superdir (e.g. "DevClub", "Business & Consulting Club")
    name = Column(String, unique=True, nullable=False, index=True)
    # Stable Superdir club_id (e.g. "devclub", "bnc")
    external_club_id = Column(String, unique=True, nullable=True, index=True)
    org_type = Column(String, nullable=False, index=True)
    banner_url = Column(String, nullable=True)
    genres = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    events = relationship("Event", back_populates="organization", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan")
