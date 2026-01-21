/**
 * Hook for real-time execution status updates via WebSocket
 * Falls back to polling if WebSocket is unavailable
 */

import { useState, useEffect, useCallback, useRef } from "react";
import {
  ExecutionStatus,
  SessionProgress,
  AgentExecution,
  Plan,
  getSessionStatus,
  getSessionProgress,
  getSessionAgents,
  getSessionPlan,
} from "../api/status";

const WS_BASE = "ws://localhost:8000";
const POLL_INTERVAL = 2000; // 2 seconds fallback
const WS_PING_INTERVAL = 25000; // 25 seconds (server timeout is 30s)
const WS_RECONNECT_DELAY = 3000; // 3 seconds before reconnect attempt
const WS_MAX_RECONNECT_ATTEMPTS = 5;

export interface WebSocketEvent {
  type: string;
  session_id: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface ActivityLogEntry {
  id: string;
  timestamp: Date;
  type: "phase" | "agent" | "tool" | "message" | "error" | "complete";
  content: string;
  details?: Record<string, unknown>;
}

export interface UseExecutionStatusResult {
  status: ExecutionStatus | null;
  progress: SessionProgress | null;
  agents: AgentExecution[];
  plan: Plan | null;
  activityLog: ActivityLogEntry[];
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useExecutionStatus(sessionId: string | null): UseExecutionStatusResult {
  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [progress, setProgress] = useState<SessionProgress | null>(null);
  const [agents, setAgents] = useState<AgentExecution[]>([]);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [activityLog, setActivityLog] = useState<ActivityLogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Add entry to activity log
  const addLogEntry = useCallback((entry: Omit<ActivityLogEntry, "id" | "timestamp">) => {
    setActivityLog((prev) => [
      {
        ...entry,
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`,
        timestamp: new Date(),
      },
      ...prev.slice(0, 99), // Keep last 100 entries
    ]);
  }, []);

  // Handle WebSocket message
  const handleWebSocketMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);

        switch (data.type) {
          case "session.started":
            addLogEntry({
              type: "message",
              content: "Research session started",
              details: data.data,
            });
            break;

          case "phase.changed":
            addLogEntry({
              type: "phase",
              content: `Phase changed to ${data.data.phase}`,
              details: data.data,
            });
            break;

          case "agent.started":
            addLogEntry({
              type: "agent",
              content: `Agent ${data.data.agent} started`,
              details: data.data,
            });
            break;

          case "agent.progress":
            // Update status with progress
            setStatus((prev) =>
              prev
                ? {
                    ...prev,
                    active_agent: data.data.agent as string,
                    progress: data.data.progress as number,
                  }
                : null
            );
            break;

          case "agent.completed":
            addLogEntry({
              type: "agent",
              content: `Agent ${data.data.agent} completed`,
              details: data.data,
            });
            break;

          case "tool.invoked":
            addLogEntry({
              type: "tool",
              content: `Tool ${data.data.tool} invoked`,
              details: data.data,
            });
            break;

          case "tool.completed":
            addLogEntry({
              type: "tool",
              content: `Tool ${data.data.tool} completed`,
              details: data.data,
            });
            break;

          case "plan.created":
            setPlan(data.data.plan as Plan);
            addLogEntry({
              type: "message",
              content: "Research plan created",
              details: data.data,
            });
            break;

          case "session.completed":
            addLogEntry({
              type: "complete",
              content: "Research completed",
              details: data.data,
            });
            break;

          case "session.error":
            setError(data.data.error as string);
            addLogEntry({
              type: "error",
              content: `Error: ${data.data.error}`,
              details: data.data,
            });
            break;

          case "status.update":
            // Full status update
            if (data.data.status) {
              setStatus(data.data.status as ExecutionStatus);
            }
            break;
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    },
    [addLogEntry]
  );

  // Fetch all data via REST
  const fetchData = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    try {
      const [statusData, progressData, agentsData, planData] = await Promise.all([
        getSessionStatus(sessionId),
        getSessionProgress(sessionId),
        getSessionAgents(sessionId),
        getSessionPlan(sessionId),
      ]);

      if (statusData) setStatus(statusData);
      if (progressData) setProgress(progressData);
      setAgents(agentsData);
      if (planData) setPlan(planData);
      setError(null);
    } catch (err) {
      setError("Failed to fetch status");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  // Connect WebSocket with reconnection support
  useEffect(() => {
    if (!sessionId) {
      setStatus(null);
      setProgress(null);
      setAgents([]);
      setPlan(null);
      setActivityLog([]);
      return;
    }

    // Initial data fetch
    fetchData();

    // Cleanup function for intervals/timeouts
    const cleanup = () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    // Start polling as initial fallback (will be cleared if WS connects)
    if (!pollIntervalRef.current) {
      pollIntervalRef.current = setInterval(fetchData, POLL_INTERVAL);
    }

    const connectWebSocket = () => {
      // Don't reconnect if we've exceeded max attempts
      if (reconnectAttemptsRef.current >= WS_MAX_RECONNECT_ATTEMPTS) {
        console.warn("Max WebSocket reconnect attempts reached, using polling only");
        return;
      }

      try {
        const ws = new WebSocket(`${WS_BASE}/ws/${sessionId}`);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          reconnectAttemptsRef.current = 0; // Reset on successful connection
          addLogEntry({
            type: "message",
            content: "Connected to execution stream",
          });

          // Clear polling since WebSocket is connected
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }

          // Start sending periodic pings to keep connection alive
          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
          }
          pingIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: "ping" }));
            }
          }, WS_PING_INTERVAL);
        };

        ws.onmessage = (event) => {
          // Handle pong from server (keep-alive response)
          try {
            const data = JSON.parse(event.data);
            if (data.type === "pong" || data.type === "ping") {
              // Server sent ping, respond with pong
              if (data.type === "ping" && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "pong" }));
              }
              return; // Don't process further
            }
          } catch {
            // Not JSON, pass to handler
          }
          handleWebSocketMessage(event);
        };

        ws.onerror = (event) => {
          console.warn("WebSocket error, falling back to polling", event);
          setIsConnected(false);
        };

        ws.onclose = (event) => {
          setIsConnected(false);

          // Clear ping interval
          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
            pingIntervalRef.current = null;
          }

          // Start polling as fallback
          if (!pollIntervalRef.current) {
            pollIntervalRef.current = setInterval(fetchData, POLL_INTERVAL);
          }

          // Attempt reconnection if not a clean close
          if (event.code !== 1000 && reconnectAttemptsRef.current < WS_MAX_RECONNECT_ATTEMPTS) {
            reconnectAttemptsRef.current++;
            const delay = WS_RECONNECT_DELAY * reconnectAttemptsRef.current; // Exponential backoff
            console.log(`WebSocket closed, attempting reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current})`);
            reconnectTimeoutRef.current = setTimeout(connectWebSocket, delay);
          }
        };
      } catch (err) {
        console.error("Failed to create WebSocket:", err);
        // Polling is already running as fallback
      }
    };

    // Initial WebSocket connection attempt
    connectWebSocket();

    return cleanup;
  }, [sessionId, fetchData, handleWebSocketMessage, addLogEntry]);

  // Manual refresh
  const refresh = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return {
    status,
    progress,
    agents,
    plan,
    activityLog,
    isConnected,
    isLoading,
    error,
    refresh,
  };
}
