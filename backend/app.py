from fastapi import Depends, FastAPI, HTTPException, status
#alextest fastapi add: HTTPException, status

from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import ADTEvent, Patient

#alextest
from sqlalchemy.exc import IntegrityError

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ADT Feed Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/patients/{mrn}/events")
def get_patient_events(mrn: str, db: Session = Depends(get_db)):
    """Return all ADT events for a given patient MRN, newest first."""
    events = (
        db.query(ADTEvent)
        .filter(ADTEvent.patient_mrn == mrn)
        .order_by(ADTEvent.event_timestamp.desc())
        .all()
    )

    return [
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
    return {"id": patient.id, "mrn": patient.mrn, "first_name": patient.first_name, 
            "last_name": patient.last_name, "date_of_birth": patient.date_of_birth, 
            "gender": patient.gender, "created_at": patient.created_at}