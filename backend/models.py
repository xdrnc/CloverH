from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mrn = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(String(10), nullable=True)
    gender = Column(String(1), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ADTEvent(Base):
    __tablename__ = "adt_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(100), unique=True, nullable=False)
    patient_mrn = Column(String(50), nullable=False, index=True)
    event_type = Column(String(10), nullable=False)
    event_description = Column(String(200), nullable=False)
    event_timestamp = Column(DateTime, nullable=False)
    sending_facility = Column(String(100), nullable=True)
    patient_class = Column(String(10), nullable=True)
    patient_location = Column(String(200), nullable=True)
    raw_message = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
