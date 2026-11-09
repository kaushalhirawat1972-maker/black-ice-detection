/**
 * Ready-to-use React Hook for BLACK ICE DETECTION.
 * Automatically connects to the FastAPI WebSocket, listens for live telemetry,
 * and handles automatic reconnection if the connection drops.
 */

import { useState, useEffect, useRef } from "react";
import { BlackIceTelemetry } from "./types";

export function useLiveTelemetry(wsUrl: string = "ws://localhost:8000/ws/live") {
  const [telemetry, setTelemetry] = useState<BlackIceTelemetry | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let shouldReconnect = true;

    function connect() {
      try {
        const ws = new WebSocket(wsUrl);
        socketRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          setError(null);
          console.log("[BLACK ICE DETECTION] WebSocket connected to:", wsUrl);
        };

        ws.onmessage = (event) => {
          try {
            const data: BlackIceTelemetry = JSON.parse(event.data);
            setTelemetry(data);
          } catch (err) {
            console.error("Error parsing telemetry packet:", err);
          }
        };

        ws.onerror = (err) => {
          console.warn("WebSocket error:", err);
          setError("Connection error");
        };

        ws.onclose = () => {
          setIsConnected(false);
          if (shouldReconnect) {
            console.log("Reconnecting in 2 seconds...");
            setTimeout(connect, 2000);
          }
        };
      } catch (err: any) {
        setError(err.message);
      }
    }

    connect();

    return () => {
      shouldReconnect = false;
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [wsUrl]);

  return { telemetry, isConnected, error };
}
