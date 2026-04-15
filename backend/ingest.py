"""Ingest HL7 ADT feed files into the database.

Reads an HL7 file and batch-loads all messages into the database.
Duplicates are automatically skipped, so re-runs are safe.

Usage:
    python ingest.py <file_path>
    python ingest.py sample_data/adt_feeds.hl7
"""

import sys

from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from hl7_parser import parse_adt_message, split_hl7_batch
from models import ADTEvent, Patient


def ingest_message(db: Session, parsed: dict) -> bool:
    """Insert a single parsed ADT message into the database.

    Creates the patient if they don't exist, then creates the ADT event.
    Returns True if the event was inserted, False if it was a duplicate.
    """
    existing = db.query(Patient).filter(Patient.mrn == parsed["patient_mrn"]).first()
    if not existing:
        patient = Patient(
            mrn=parsed["patient_mrn"],
            first_name=parsed["first_name"],
            last_name=parsed["last_name"],
            date_of_birth=parsed["date_of_birth"],
            gender=parsed["gender"],
        )
        db.add(patient)
        db.flush()

    duplicate = (
        db.query(ADTEvent)
        .filter(ADTEvent.message_id == parsed["message_id"])
        .first()
    )
    if duplicate:
        return False

    event = ADTEvent(
        message_id=parsed["message_id"],
        patient_mrn=parsed["patient_mrn"],
        event_type=parsed["event_type"],
        event_description=parsed["event_description"],
        event_timestamp=parsed["event_timestamp"],
        sending_facility=parsed["sending_facility"],
        patient_class=parsed["patient_class"],
        patient_location=parsed["patient_location"],
        raw_message=parsed["raw_message"],
    )
    db.add(event)
    return True


def ingest_file(file_path: str):
    """Read an HL7 file and batch-load all messages into the database."""
    Base.metadata.create_all(bind=engine)

    with open(file_path) as f:
        content = f.read()

    messages = split_hl7_batch(content)
    print(f"Found {len(messages)} message(s) in {file_path}")

    db = SessionLocal()
    inserted = 0
    skipped = 0

    for raw in messages:
        parsed = parse_adt_message(raw)
        if ingest_message(db, parsed):
            inserted += 1
        else:
            skipped += 1

    db.commit()
    db.close()
    print(f"Done — Inserted: {inserted}, Skipped (duplicate): {skipped}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python ingest.py <hl7_file_path>")
        sys.exit(1)

    ingest_file(sys.argv[1])
