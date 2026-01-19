/**
 * Tool Management API
 *
 * Functions for interacting with the tool registry:
 * - List, create, delete tools
 * - Execute and test tools
 * - Manage tool status
 */

const API_BASE = "http://localhost:8000/api";

// Types
export type ToolCategory = "browser" | "file" | "code" | "data" | "api" | "math" | "custom";
export type ToolStatus = "active" | "disabled" | "error";

export interface ToolSummary {
  name: string;
  description: string;
  category: ToolCategory;
  is_builtin: boolean;
  status: ToolStatus;
  execution_count: number;
  allowed_agents: string[];
}

export interface ToolDetail extends ToolSummary {
  created_at: string;
  updated_at: string;
  last_execution: string | null;
  source_code: string | null;
  error_message: string | null;
}

export interface ToolRegistryStatus {
  total_tools: number;
  active_tools: number;
  builtin_tools: number;
  custom_tools: number;
  tools: ToolSummary[];
}

export interface ToolCreateRequest {
  name: string;
  description: string;
  code: string;
  category?: ToolCategory;
  allowed_agents?: string[];
}

export interface ToolExecuteRequest {
  name: string;
  args: Record<string, unknown>;
}

export interface ToolExecuteResult {
  success: boolean;
  tool_name: string;
  result?: string;
  error?: string;
  execution_time_ms?: number;
}

/**
 * Get all registered tools with registry status
 */
export async function listTools(): Promise<ToolRegistryStatus> {
  const response = await fetch(`${API_BASE}/tools/`);
  if (!response.ok) throw new Error("Failed to list tools");
  return response.json();
}

/**
 * Get detailed information about a specific tool
 */
export async function getTool(toolName: string): Promise<ToolDetail> {
  const response = await fetch(`${API_BASE}/tools/${toolName}`);
  if (!response.ok) throw new Error(`Tool '${toolName}' not found`);
  return response.json();
}

/**
 * Create a new dynamic tool
 */
export async function createTool(request: ToolCreateRequest): Promise<{ success: boolean; message: string; tool_name: string }> {
  const response = await fetch(`${API_BASE}/tools/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create tool");
  }
  return response.json();
}

/**
 * Execute a tool with given arguments (for testing)
 */
export async function executeTool(toolName: string, args: Record<string, unknown> = {}): Promise<ToolExecuteResult> {
  const response = await fetch(`${API_BASE}/tools/${toolName}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: toolName, args }),
  });
  if (!response.ok) throw new Error(`Failed to execute tool '${toolName}'`);
  return response.json();
}

/**
 * Update tool status (active, disabled, error)
 */
export async function updateToolStatus(
  toolName: string,
  status: ToolStatus,
  errorMessage?: string
): Promise<{ success: boolean; tool_name: string; status: string }> {
  const response = await fetch(`${API_BASE}/tools/${toolName}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, error_message: errorMessage }),
  });
  if (!response.ok) throw new Error(`Failed to update status for '${toolName}'`);
  return response.json();
}

/**
 * Delete a custom tool (built-in tools cannot be deleted)
 */
export async function deleteTool(toolName: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/tools/${toolName}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Failed to delete tool '${toolName}'`);
  }
  return response.json();
}

/**
 * List tools in a specific category
 */
export async function listToolsByCategory(category: ToolCategory): Promise<{
  category: string;
  count: number;
  tools: { name: string; description: string }[];
}> {
  const response = await fetch(`${API_BASE}/tools/category/${category}`);
  if (!response.ok) throw new Error(`Failed to list tools in category '${category}'`);
  return response.json();
}

/**
 * List tools available to a specific agent type
 */
export async function listToolsForAgent(agentType: string): Promise<{
  agent_type: string;
  count: number;
  tools: { name: string; description: string }[];
}> {
  const response = await fetch(`${API_BASE}/tools/agent/${agentType}`);
  if (!response.ok) throw new Error(`Failed to list tools for agent '${agentType}'`);
  return response.json();
}

// Category display info
export const CATEGORY_INFO: Record<ToolCategory, { label: string; color: string; bgColor: string }> = {
  browser: { label: "Browser", color: "text-blue-400", bgColor: "bg-blue-500/20" },
  file: { label: "File", color: "text-amber-400", bgColor: "bg-amber-500/20" },
  code: { label: "Code", color: "text-purple-400", bgColor: "bg-purple-500/20" },
  data: { label: "Data", color: "text-emerald-400", bgColor: "bg-emerald-500/20" },
  api: { label: "API", color: "text-cyan-400", bgColor: "bg-cyan-500/20" },
  math: { label: "Math", color: "text-orange-400", bgColor: "bg-orange-500/20" },
  custom: { label: "Custom", color: "text-pink-400", bgColor: "bg-pink-500/20" },
};

// Status display info
export const STATUS_INFO: Record<ToolStatus, { label: string; color: string; bgColor: string }> = {
  active: { label: "Active", color: "text-emerald-400", bgColor: "bg-emerald-500/20" },
  disabled: { label: "Disabled", color: "text-slate-400", bgColor: "bg-slate-500/20" },
  error: { label: "Error", color: "text-red-400", bgColor: "bg-red-500/20" },
};
