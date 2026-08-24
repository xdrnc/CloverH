"""WebSocket connection manager for real-time ADT events."""
from typing import Set, Dict
from fastapi import WebSocket
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # mrn -> set of WebSocket connections
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> set of MRNs it's subscribed to
        self.client_mrns: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, mrns: list[str]):
        await websocket.accept()
        async with self._lock:
            self.client_mrns[websocket] = set(mrns)
            for mrn in mrns:
                if mrn not in self.subscriptions:
                    self.subscriptions[mrn] = set()
                self.subscriptions[mrn].add(websocket)
        logger.info(f"Client connected, subscribed to: {mrns}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            mrns = self.client_mrns.pop(websocket, set())
            for mrn in mrns:
                self.subscriptions[mrn].discard(websocket)
                if not self.subscriptions[mrn]:
                    del self.subscriptions[mrn]
        logger.info(f"Client disconnected, was subscribed to: {mrns}")

    async def broadcast_to_mrn(self, mrn: str, message: dict):
        """Send message to all clients subscribed to a specific MRN."""
        async with self._lock:
            targets = list(self._subscriptions.get(mrn, set()))
        
        dead = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        
        for ws in dead:
            await self.disconnect(ws)

    async def broadcast_all(self, message: dict):
        """Broadcast to all connected clients."""
        async with self._lock:
            targets = list(self._client_mrns.keys())
        
        dead = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        
        for ws in dead:
            await self.disconnect(ws)

    def get_subscriber_count(self, mrn: str = None) -> int:
        """Get count of subscribers for an MRN or total."""
        if mrn:
            return len(self.subscriptions.get(mrn, set()))
        return len(self.client_mrns)


# Singleton instance
manager = ConnectionManager()