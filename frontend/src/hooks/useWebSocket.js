import { useEffect, useRef, useState } from "react";
import { getStoredToken } from "../services/api";

/**
 * Connects to the backend's /ws endpoint (token passed as a query param -
 * browsers' native WebSocket API can't set an Authorization header) and
 * calls `onMessage` for every parsed JSON message received.
 *
 * Auto-reconnects with a fixed backoff if the connection drops, and
 * cleanly closes on unmount. Returns the current connection status so UI
 * can show a "live" / "reconnecting" indicator instead of pretending the
 * feed is always live.
 */
export function useWebSocket(onMessage) {
  const [status, setStatus] = useState("connecting"); // connecting | open | closed
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let socket;
    let reconnectTimer;
    let cancelled = false;

    function connect() {
      const token = getStoredToken();
      if (!token) {
        setStatus("closed");
        return;
      }

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const url = `${protocol}//${window.location.host}/ws?token=${encodeURIComponent(token)}`;
      socket = new WebSocket(url);

      socket.onopen = () => {
        if (!cancelled) setStatus("open");
      };

      socket.onmessage = (event) => {
        if (cancelled) return;
        try {
          const message = JSON.parse(event.data);
          onMessageRef.current?.(message);
        } catch {
          // Ignore malformed messages rather than crashing the UI.
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        setStatus("closed");
        reconnectTimer = window.setTimeout(connect, 3000);
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return status;
}
