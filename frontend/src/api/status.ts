/**
 * Status API - Endpoints for execution tracking and session status
 */

const API_BASE = "http://localhost:8000/api";

export interface ExecutionPhase {
  name: string;
  key: string;
  progress: number;
  weight: number;
  is_current: boolean;
  is_completed: boolean;
  status: "pending" | "current" | "completed";
}

export interface ToolExecution {
  tool: string;
  success: boolean;
  started_at: string;
  completed_at: string | null;
}

export interface AgentExecution {
  agent: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  progress?: number;
  tools_used: ToolExecution[];
  result_summary?: string;
}

export interface PlanTask {
  id: number;
  description: string;
  assigned_agent: string;
  status: string;
  dependencies?: number[];
}

export interface Plan {
  main_goal: string;
  tasks: PlanTask[];
  scope?: {
    scope: string;
    target_pages: number;
    target_word_count: number;
  };
}

export type PlanApprovalStatus = "pending" | "approved" | "rejected" | "modified";

export interface TaskUpdate {
  description?: string;
  assigned_agent?: string;
  status?: string;
  dependencies?: number[];
}

export interface TaskCreate {
  description: string;
  assigned_agent: string;
  dependencies?: number[];
  position?: number;
}

export interface PlanApprovalRequest {
  approved: boolean;
  modifications?: {
    main_goal?: string;
    tasks?: PlanTask[];
  };
}

export interface ExecutionStatus {
  session_id: string;
  current_phase: string;
  progress: number;
  active_agent: string | null;
  active_tools: string[];
  plan: Plan | null;
  plan_approval_status: PlanApprovalStatus;
  plan_waiting_approval: boolean;
  started_at: string;
  updated_at: string;
  completed_at: string | null;
  error: string | null;
  messages: string[];
  phase_progress: Record<string, number>;
  estimated_completion: string | null;
}

export interface SessionProgress {
  overall_progress: number;
  current_phase: string;
  phases: ExecutionPhase[];
  started_at: string;
  estimated_completion: string | null;
}

// Get session status
export async function getSessionStatus(sessionId: string): Promise<ExecutionStatus | null> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}`);
    if (!response.ok) return null;
    const data = await response.json();
    return data.status;
  } catch (error) {
    console.error("Failed to fetch session status:", error);
    return null;
  }
}

// Get session progress with phase breakdown
export async function getSessionProgress(sessionId: string): Promise<SessionProgress | null> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}/progress`);
    if (!response.ok) return null;
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Failed to fetch session progress:", error);
    return null;
  }
}

// Get session plan
export async function getSessionPlan(sessionId: string): Promise<Plan | null> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}/plan`);
    if (!response.ok) return null;
    const data = await response.json();
    return data.plan;
  } catch (error) {
    console.error("Failed to fetch session plan:", error);
    return null;
  }
}

// Get agent execution history
export async function getSessionAgents(sessionId: string): Promise<AgentExecution[]> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}/agents`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.agents || [];
  } catch (error) {
    console.error("Failed to fetch session agents:", error);
    return [];
  }
}

// Get status messages
export async function getSessionMessages(sessionId: string, limit: number = 50): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}/messages?limit=${limit}`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.messages || [];
  } catch (error) {
    console.error("Failed to fetch session messages:", error);
    return [];
  }
}

// List active sessions
export async function listActiveSessions(): Promise<{ session_id: string; phase: string; progress: number }[]> {
  try {
    const response = await fetch(`${API_BASE}/status/?active_only=true`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.sessions || [];
  } catch (error) {
    console.error("Failed to fetch active sessions:", error);
    return [];
  }
}

// Update a task in the plan
export async function updatePlanTask(
  sessionId: string,
  taskId: number,
  updates: TaskUpdate
): Promise<PlanTask | null> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}/plan/task/${taskId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });
    if (!response.ok) return null;
    const data = await response.json();
    return data.task;
  } catch (error) {
    console.error("Failed to update task:", error);
    return null;
  }
}

// Add a new task to the plan
export async function addPlanTask(
  sessionId: string,
  task: TaskCreate
): Promise<PlanTask | null> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}/plan/task`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(task),
    });
    if (!response.ok) return null;
    const data = await response.json();
    return data.task;
  } catch (error) {
    console.error("Failed to add task:", error);
    return null;
  }
}

// Remove a task from the plan
export async function removePlanTask(
  sessionId: string,
  taskId: number
): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}/plan/task/${taskId}`, {
      method: "DELETE",
    });
    return response.ok;
  } catch (error) {
    console.error("Failed to remove task:", error);
    return false;
  }
}

// Reorder tasks in the plan
export async function reorderPlanTasks(
  sessionId: string,
  taskOrder: number[]
): Promise<Plan | null> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}/plan/reorder`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_order: taskOrder }),
    });
    if (!response.ok) return null;
    const data = await response.json();
    return data.plan;
  } catch (error) {
    console.error("Failed to reorder tasks:", error);
    return null;
  }
}

// Approve or reject the plan
export async function approvePlan(
  sessionId: string,
  approval: PlanApprovalRequest
): Promise<{ approved: boolean; approval_status: PlanApprovalStatus } | null> {
  try {
    const response = await fetch(`${API_BASE}/status/${sessionId}/plan/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(approval),
    });
    if (!response.ok) return null;
    const data = await response.json();
    return {
      approved: data.approved,
      approval_status: data.approval_status,
    };
  } catch (error) {
    console.error("Failed to approve plan:", error);
    return null;
  }
}
