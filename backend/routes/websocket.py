"""WebSocket routes for real-time ADT events."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional
import asyncio
import logging

from websocket_manager import manager
from cache import cache, events_cache_key
from database import get_db
from models import ADTEvent
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter()


def get_cached_or_fetch_events(mrn: str, db: Session):
    """Helper to get events from cache or DB."""
    key = events_cache_key(mrn)
    cached = cache.get(key)
    if cached:
        return cached
    
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
    cache.set(key, response)
    return response


@router.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    mrns: Optional[str] = Query(None, description="Comma-separated MRNs to subscribe to"),
    db: Session = Depends(get_db)
):
    """WebSocket for real-time ADT events.
    
    Query param: mrns=MRN1,MRN2,MRN3 (comma-separated)
    If empty, subscribes to all events (broadcast mode).
    """
    mrn_list = [m.strip() for m in mrns.split(",") if m.strip()] if mrns else []
    await manager.connect(websocket, mrn_list)
    
    try:
        # Send initial state for subscribed MRNs
        if mrn_list:
            for mrn in mrn_list:
                events = get_cached_or_fetch_events(mrn, db)
                await websocket.send_json({
                    "type": "initial",
                    "mrn": mrn,
                    "events": events
                })
        else:
            await websocket.send_json({"type": "connected", "subscribed": "all"})
        
        # Keep connection alive - handle ping/pong or client messages
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)