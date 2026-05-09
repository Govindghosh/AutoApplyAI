"use client";

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import { backendApi } from "@/lib/backend-api";
import { appConfig, getTelemetryWebSocketUrl } from "@/lib/config";
import type { TelemetryEvent } from "@/lib/types";

interface TelemetryContextType {
  events: TelemetryEvent[];
  isConnected: boolean;
  clearEvents: () => void;
}

const TelemetryContext = createContext<TelemetryContextType | undefined>(undefined);

export const TelemetryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const connectRef = useRef<() => void>(() => {});

  const fetchHistory = useCallback(async () => {
    try {
      const history = await backendApi.telemetry.history();
      setEvents(history);
    } catch (err) {
      console.error("Failed to fetch event history:", err);
    }
  }, []);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;

    const token = localStorage.getItem("access_token");
    if (!token) {
      console.warn("No access token found for telemetry connection");
      return;
    }

    // Fetch history first for catch-up
    fetchHistory();

    const wsUrl = getTelemetryWebSocketUrl(token);

    console.log("Telemetry connecting to:", wsUrl);
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("Telemetry stream connected successfully");
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as TelemetryEvent;
        setEvents((prev) => {
          // Idempotency: Check if event already exists
          if (data.event_id && prev.some((e) => e.event_id === data.event_id)) return prev;
          return [data, ...prev].slice(0, appConfig.telemetryEventLimit);
        }); 
        window.dispatchEvent(new CustomEvent("telemetry_event", { detail: data }));
      } catch (err) {
        console.error("Telemetry parse error:", err);
      }
    };

    ws.onclose = (event) => {
      console.log("Telemetry stream closed:", event.code, event.reason);
      setIsConnected(false);
      if (event.code !== 1000) {
        // Backoff reconnection
        reconnectTimerRef.current = window.setTimeout(
          () => connectRef.current(),
          appConfig.telemetryReconnectMs
        );
      }
    };

    ws.onerror = () => {
      console.error("Telemetry WebSocket error occurred. Check backend logs for authentication or CORS issues.");
      ws.close();
    };

    socketRef.current = ws;
  }, [fetchHistory]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    const startTimer = window.setTimeout(() => connect(), 0);
    return () => {
      window.clearTimeout(startTimer);
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close(1000);
    };
  }, [connect]);

  const clearEvents = () => setEvents([]);

  return (
    <TelemetryContext.Provider value={{ events, isConnected, clearEvents }}>
      {children}
    </TelemetryContext.Provider>
  );
};

export const useTelemetry = () => {
  const context = useContext(TelemetryContext);
  if (!context) throw new Error("useTelemetry must be used within TelemetryProvider");
  return context;
};
