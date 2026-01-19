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

  // Add entry to activity log
  const addLogEntry = useCallback((entry: Omit<ActivityLogEntry, "id" | "timestamp">) => {
    setActivityLog((prev) => [
      {
        ...entry,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
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

  // Connect WebSocket
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

    // Try WebSocket connection
    const ws = new WebSocket(`${WS_BASE}/ws/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      addLogEntry({
        type: "message",
        content: "Connected to execution stream",
      });

      // Clear polling if WebSocket connects
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };

    ws.onmessage = handleWebSocketMessage;

    ws.onerror = () => {
      console.warn("WebSocket error, falling back to polling");
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);

      // Start polling as fallback
      if (!pollIntervalRef.current) {
        pollIntervalRef.current = setInterval(fetchData, POLL_INTERVAL);
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;

      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
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
