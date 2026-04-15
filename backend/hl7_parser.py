"""Minimal HL7 v2.x ADT message parser."""

from datetime import datetime

from dateutil.parser import parse as parse_date

EVENT_TYPES = {
    "A01": "Admit",
    "A02": "Transfer",
    "A03": "Discharge",
    "A04": "Register",
    "A08": "Update Patient Info",
    "A11": "Cancel Admit",
    "A12": "Cancel Transfer",
    "A13": "Cancel Discharge",
}


def _get_field(segment: str, index: int, component: int = 0) -> str:
    """Extract a field from an HL7 segment by index (1-based for non-MSH, 0-based offset)."""
    fields = segment.split("|")
    if index >= len(fields):
        return ""
    field = fields[index]
    if component > 0:
        components = field.split("^")
        if component - 1 < len(components):
            return components[component - 1]
        return ""
    return field


def _parse_hl7_timestamp(ts: str) -> datetime:
    """Parse an HL7 timestamp like 20230101120000 into a datetime."""
    if not ts:
        return datetime.now()
    # HL7 timestamps: YYYYMMDDHHMMSS
    if len(ts) >= 14:
        return datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
    if len(ts) >= 8:
        return datetime.strptime(ts[:8], "%Y%m%d")
    return parse_date(ts)


def parse_adt_message(raw: str) -> dict:
    """Parse a single HL7 ADT message into a structured dict.

    Returns a dict with keys:
        message_id, event_type, event_description, event_timestamp,
        sending_facility, patient_mrn, first_name, last_name,
        date_of_birth, gender, patient_class, patient_location, raw_message
    """
    segments = {}
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        seg_type = line[:3]
        segments[seg_type] = line

    msh = segments.get("MSH", "")
    pid = segments.get("PID", "")
    pv1 = segments.get("PV1", "")
    evn = segments.get("EVN", "")

    # MSH: field separator is MSH-1 (|), so MSH fields are offset by 1
    # MSH|^~\&|SendingApp|SendingFacility|ReceivingApp|ReceivingFacility|Timestamp||MsgType|MsgControlID|ProcessingID|Version
    message_id = _get_field(msh, 9)  # MSH-10 (0-indexed: 9)
    msg_type_field = _get_field(msh, 8)  # MSH-9
    event_code = msg_type_field.split("^")[1] if "^" in msg_type_field else ""
    sending_facility = _get_field(msh, 3)  # MSH-4
    msg_timestamp_str = _get_field(msh, 6)  # MSH-7

    # EVN segment
    evn_timestamp_str = _get_field(evn, 2) if evn else ""
    event_timestamp = _parse_hl7_timestamp(evn_timestamp_str or msg_timestamp_str)

    # PID: PID|SetID|ExtPatientID|PatientID|AltPatientID|PatientName|...
    patient_mrn = _get_field(pid, 3, component=1)  # PID-3.1
    last_name = _get_field(pid, 5, component=1)  # PID-5.1
    first_name = _get_field(pid, 5, component=2)  # PID-5.2
    dob = _get_field(pid, 7)  # PID-7
    gender = _get_field(pid, 8)  # PID-8

    # PV1: PV1|SetID|PatientClass|AssignedLocation|...
    patient_class = _get_field(pv1, 2)  # PV1-2
    location_field = _get_field(pv1, 3)  # PV1-3
    patient_location = location_field.replace("^", " ").strip()

    event_description = EVENT_TYPES.get(event_code, f"Unknown ({event_code})")

    return {
        "message_id": message_id,
        "event_type": event_code,
        "event_description": event_description,
        "event_timestamp": event_timestamp,
        "sending_facility": sending_facility,
        "patient_mrn": patient_mrn,
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": dob,
        "gender": gender,
        "patient_class": patient_class,
        "patient_location": patient_location,
        "raw_message": raw,
    }


def split_hl7_batch(content: str) -> list[str]:
    """Split a file containing multiple HL7 messages separated by blank lines."""
    messages = []
    current = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped and current:
            messages.append("\n".join(current))
            current = []
        elif stripped:
            current.append(stripped)
    if current:
        messages.append("\n".join(current))
    return messages
