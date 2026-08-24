from fastapi import Depends, FastAPI, HTTPException, status
#alextest fastapi add: HTTPException, status

from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import ADTEvent, Patient

#alextest
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from cache import cache, events_cache_key, invalidate_events_cache
from routes.websocket import router as websocket_router
from websocket_manager import manager
import asyncio

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ADT Feed Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WebSocket router
app.include_router(websocket_router)

# Hook cache invalidation to WebSocket broadcast
def on_events_cache_invalidated(prefix: str):
    if prefix == "events:" or prefix == "*":
        asyncio.create_task(manager.broadcast_all({"type": "cache_invalidated"}))

cache.on_invalidate(on_events_cache_invalidated)


@app.get("/api/patients")
def list_patients(db: Session = Depends(get_db)):
    """Return all patients who have at least one ADT event."""
    mrns_with_events = (
        db.query(distinct(ADTEvent.patient_mrn)).all()
    )
    mrn_list = [row[0] for row in mrns_with_events]

    patients = (
        db.query(Patient)
        .filter(Patient.mrn.in_(mrn_list))
        .order_by(Patient.last_name, Patient.first_name)
        .all()
    )

    return [
        {
            "mrn": p.mrn,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "date_of_birth": p.date_of_birth,
            "gender": p.gender,
        }
        for p in patients
    ]

@app.get("/api/patients2")
def list_patients2(
    page: int = 1,
    pageSize: int = 3,
    db: Session = Depends(get_db)):

    query = (db.query(Patient)
            .join(ADTEvent, Patient.mrn == ADTEvent.patient_mrn)
            .group_by(Patient.id)) #AlexNote: need .group_by(Patient.id) because without it, a patient with 5 events would appear 5 times in your result list.

    total = query.count()

    patients = (query 
                .order_by(Patient.last_name, Patient.first_name)
                .offset((page-1) * pageSize) #AlexNote: offset = skip first few items
                .limit(pageSize)
                .all())

    return {
        "patients":[
            {
            "mrn": p.mrn,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "date_of_birth": p.date_of_birth,
            "gender": p.gender,
            }
            for p in patients
        ],
        "page" : page,
        "pageSize" : pageSize,
        "total" : total,
        "totalPages" : (total + pageSize - 1) // pageSize
    }

@app.get("/api/patients/{mrn}/events")
def get_patient_events(mrn: str, db: Session = Depends(get_db)):
    """Return all ADT events for a given patient MRN, newest first."""
    key = events_cache_key(mrn)
    
    # Try cache first
    cached = cache.get(key)
    if cached:
        return cached
    
    # Cache miss: query DB
    events = (
        db.query(ADTEvent)
        .filter(ADTEvent.patient_mrn == mrn)
        .order_by(ADTEvent.event_timestamp.desc())
        .all()
    )

    response = [
        {
            "id": e.id,
            "message_id": e.message_id,
            "event_type": e.event_type,
            "event_description": e.event_description,
            "event_timestamp": e.event_timestamp.isoformat(),
            "sending_facility": e.sending_facility,
            "patient_class": e.patient_class,
            "patient_location": e.patient_location,
        }
        for e in events
    ]
    
    # Store in cache
    cache.set(key, response)
    return response


#alextest post new patient
@app.post("/api/patients", status_code=status.HTTP_201_CREATED)
def create_patient(mrn: str, first_name: str, last_name: str, 
                   date_of_birth: str = None, gender: str = None, 
                   db: Session = Depends(get_db)):
    patient = Patient(
        mrn=mrn,
        first_name= first_name,
        last_name= last_name,
        date_of_birth=date_of_birth,
        gender=gender,
    )
    db.add(patient)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"MRN '{mrn}' already exists")
    db.refresh(patient)
    invalidate_events_cache()  # Invalidate events cache on new patient
    return {"id": patient.id, "mrn": patient.mrn, "first_name": patient.first_name, 
            "last_name": patient.last_name, "date_of_birth": patient.date_of_birth, 
            "gender": patient.gender, "created_at": patient.created_at}


@app.post("/api/events", status_code=status.HTTP_201_CREATED)
def create_event(
    message_id: str,
    patient_mrn: str,
    event_type: str,
    event_description: str,
    event_timestamp: str,  # ISO format: "2025-03-01T12:00:00"
    sending_facility: str = None,
    patient_class: str = None,
    patient_location: str = None,
    db: Session = Depends(get_db)
):
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.mrn == patient_mrn).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_mrn} not found")
    
    # Check duplicate message_id
    if db.query(ADTEvent).filter(ADTEvent.message_id == message_id).first():
        raise HTTPException(status_code=409, detail=f"Event {message_id} already exists")
    
    event = ADTEvent(
        message_id=message_id,
        patient_mrn=patient_mrn,
        event_type=event_type,
        event_description=event_description,
        event_timestamp=datetime.fromisoformat(event_timestamp),
        sending_facility=sending_facility,
        patient_class=patient_class,
        patient_location=patient_location,
        raw_message=f"MANUAL:{message_id}",  # Required field
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate or constraint error")
    db.refresh(event)
    invalidate_events_cache()  # Invalidate events cache on new event
    
    # Push to WebSocket subscribers
    event_data = {
        "id": event.id,
        "message_id": event.message_id,
        "event_type": event.event_type,
        "event_description": event.event_description,
        "event_timestamp": event.event_timestamp.isoformat(),
        "sending_facility": event.sending_facility,
        "patient_class": event.patient_class,
        "patient_location": event.patient_location,
        "patient_mrn": patient_mrn,
    }
    asyncio.create_task(manager.broadcast_to_mrn(patient_mrn, {
        "type": "event_created",
        "event": event_data
    }))
    return {"id": event.id, "message_id": event.message_id, "patient_mrn": event.patient_mrn}


# Cache management endpoints
@app.get("/api/cache/stats")
def get_cache_stats():
    """Return cache statistics."""
    return cache.stats()


@app.post("/api/cache/clear")
def clear_cache():
    """Clear all cache entries."""
    cache.clear()
    return {"message": "Cache cleared"}