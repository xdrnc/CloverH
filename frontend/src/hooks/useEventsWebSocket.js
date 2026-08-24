import { useEffect, useRef, useState, useCallback } from "react";

const WS_BASE = (() => {
  // In development, use localhost. In production, use same host.
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}`;
  }
  return "ws://localhost:8000";
})();

export function useEventsWebSocket(mrns = []) {
  const [eventsByMrn, setEventsByMrn] = useState({});
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 10;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    
    const mrnParam = mrns.join(",");
    const url = `${WS_BASE}/ws/events?mrns=${mrnParam}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setError(null);
      reconnectAttempts.current = 0;
      console.log("[WS] Connected, subscribed to:", mrns);
    };

    ws.onclose = (event) => {
      setConnected(false);
      console.log("[WS] Disconnected:", event.code, event.reason);
      
      // Exponential backoff reconnect
      if (reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
        reconnectAttempts.current++;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      } else {
        setError("Max reconnection attempts reached");
      }
    };

    ws.onerror = (err) => {
      console.error("[WS] Error:", err);
      setError("WebSocket connection error");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
      } catch (e) {
        console.error("[WS] Parse error:", e);
      }
    };
  }, [mrns]);

  const handleMessage = (msg) => {
    switch (msg.type) {
      case "initial":
        setEventsByMrn(prev => ({ 
          ...prev, 
          [msg.mrn]: msg.events 
        }));
        break;
      case "event_created":
        setEventsByMrn(prev => ({
          ...prev,
          [msg.event.patient_mrn]: [
            msg.event, 
            ...(prev[msg.event.patient_mrn] || [])
          ].slice(0, 100) // Cap at 100 events per patient
        }));
        break;
      case "cache_invalidated":
        // Could trigger a refetch if needed
        console.log("[WS] Cache invalidated");
        break;
      case "connected":
        console.log("[WS] Connected to broadcast mode");
        break;
    }
  };

  // Reconnect when mrns change
  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close();
    };
  }, []);

  return { eventsByMrn, connected, error };
}