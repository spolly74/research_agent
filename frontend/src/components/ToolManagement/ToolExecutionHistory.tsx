/**
 * ToolExecutionHistory - Shows recent tool executions with details
 * Real-time feed of tool activity with filtering and search
 */

import { useState, useEffect } from "react";
import { cn } from "../../lib/utils";
import { CATEGORY_INFO, type ToolCategory } from "../../api/tools";
import {
  History,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  Filter,
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronUp,
  Terminal,
  User,
  Wrench,
} from "lucide-react";

// Execution record type (matches backend ToolExecution model)
interface ToolExecution {
  id: number;
  tool_name: string;
  session_id: number | null;
  agent_type: string | null;
  input_args: Record<string, unknown>;
  output: string | null;
  success: boolean;
  error_message: string | null;
  execution_time_ms: number;
  created_at: string;
  category?: ToolCategory;
}

interface ToolExecutionHistoryProps {
  className?: string;
  limit?: number;
  toolName?: string; // Filter by specific tool
  sessionId?: string; // Filter by session
}

// Mock data for demonstration (in real app, this would come from API)
function generateMockExecutions(count: number): ToolExecution[] {
  const tools = [
    { name: "browser_search", category: "browser" as ToolCategory, agents: ["researcher"] },
    { name: "visit_page", category: "browser" as ToolCategory, agents: ["researcher"] },
    { name: "calculator", category: "math" as ToolCategory, agents: ["researcher", "coder"] },
    { name: "api_get", category: "api" as ToolCategory, agents: ["researcher", "coder"] },
    { name: "execute_python", category: "code" as ToolCategory, agents: ["coder"] },
    { name: "json_parser", category: "data" as ToolCategory, agents: ["researcher", "coder"] },
  ];

  const executions: ToolExecution[] = [];
  const now = Date.now();

  for (let i = 0; i < count; i++) {
    const tool = tools[Math.floor(Math.random() * tools.length)];
    const success = Math.random() > 0.15;
    const timeAgo = Math.floor(Math.random() * 3600000); // Up to 1 hour ago

    executions.push({
      id: i + 1,
      tool_name: tool.name,
      session_id: Math.floor(Math.random() * 10) + 1,
      agent_type: tool.agents[Math.floor(Math.random() * tool.agents.length)],
      input_args: { query: "example query" },
      output: success ? "Tool executed successfully" : null,
      success,
      error_message: success ? null : "Connection timeout",
      execution_time_ms: Math.floor(Math.random() * 2000) + 50,
      created_at: new Date(now - timeAgo).toISOString(),
      category: tool.category,
    });
  }

  return executions.sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function ExecutionItem({ execution }: { execution: ToolExecution }) {
  const [expanded, setExpanded] = useState(false);
  const categoryInfo = execution.category ? CATEGORY_INFO[execution.category] : null;

  return (
    <div
      className={cn(
        "bg-slate-900/30 border rounded-lg overflow-hidden transition-all",
        execution.success ? "border-slate-800" : "border-red-500/30"
      )}
    >
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-slate-800/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Status icon */}
        <div
          className={cn(
            "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
            execution.success ? "bg-emerald-500/10" : "bg-red-500/10"
          )}
        >
          {execution.success ? (
            <CheckCircle size={16} className="text-emerald-400" />
          ) : (
            <XCircle size={16} className="text-red-400" />
          )}
        </div>

        {/* Tool info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono font-medium text-sm text-slate-200">
              {execution.tool_name}
            </span>
            {categoryInfo && (
              <span
                className={cn(
                  "px-1.5 py-0.5 rounded text-[9px] font-mono uppercase",
                  categoryInfo.bgColor,
                  categoryInfo.color
                )}
              >
                {categoryInfo.label}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
            {execution.agent_type && (
              <span className="flex items-center gap-1">
                <User size={10} />
                {execution.agent_type}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock size={10} />
              {execution.execution_time_ms}ms
            </span>
          </div>
        </div>

        {/* Time */}
        <span className="text-xs text-slate-500 font-mono flex-shrink-0">
          {formatTimeAgo(execution.created_at)}
        </span>

        {/* Expand icon */}
        <div className="text-slate-500">
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-slate-800 p-3 space-y-3 bg-slate-950/30">
          {/* Input args */}
          {Object.keys(execution.input_args).length > 0 && (
            <div>
              <div className="flex items-center gap-1 text-xs text-slate-500 mb-1">
                <Terminal size={10} />
                <span>Input</span>
              </div>
              <pre className="text-xs font-mono text-slate-400 bg-slate-900 rounded p-2 overflow-x-auto">
                {JSON.stringify(execution.input_args, null, 2)}
              </pre>
            </div>
          )}

          {/* Output or error */}
          {execution.success ? (
            execution.output && (
              <div>
                <div className="flex items-center gap-1 text-xs text-emerald-500 mb-1">
                  <CheckCircle size={10} />
                  <span>Output</span>
                </div>
                <pre className="text-xs font-mono text-slate-400 bg-slate-900 rounded p-2 overflow-x-auto max-h-32">
                  {execution.output}
                </pre>
              </div>
            )
          ) : (
            <div>
              <div className="flex items-center gap-1 text-xs text-red-500 mb-1">
                <XCircle size={10} />
                <span>Error</span>
              </div>
              <pre className="text-xs font-mono text-red-400 bg-red-500/5 rounded p-2">
                {execution.error_message || "Unknown error"}
              </pre>
            </div>
          )}

          {/* Metadata */}
          <div className="flex items-center gap-4 text-xs text-slate-500 pt-2 border-t border-slate-800">
            <span>ID: {execution.id}</span>
            {execution.session_id && <span>Session: {execution.session_id}</span>}
            <span>{new Date(execution.created_at).toLocaleString()}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export function ToolExecutionHistory({
  className,
  limit = 50,
  toolName,
  sessionId,
}: ToolExecutionHistoryProps) {
  const [executions, setExecutions] = useState<ToolExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "success" | "error">("all");

  useEffect(() => {
    // In real app, fetch from API
    setLoading(true);
    setTimeout(() => {
      setExecutions(generateMockExecutions(limit));
      setLoading(false);
    }, 500);
  }, [limit, toolName, sessionId]);

  const filteredExecutions = executions.filter((e) => {
    if (filter === "success" && !e.success) return false;
    if (filter === "error" && e.success) return false;
    if (toolName && e.tool_name !== toolName) return false;
    return true;
  });

  const stats = {
    total: executions.length,
    success: executions.filter((e) => e.success).length,
    error: executions.filter((e) => !e.success).length,
    avgTime: Math.round(
      executions.reduce((sum, e) => sum + e.execution_time_ms, 0) / executions.length || 0
    ),
  };

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-slate-800 bg-slate-900/50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
              <History size={20} className="text-amber-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-200">Execution History</h2>
              <p className="text-xs text-slate-500 font-mono">
                {stats.total} executions recorded
              </p>
            </div>
          </div>

          <button
            onClick={() => {
              setLoading(true);
              setTimeout(() => {
                setExecutions(generateMockExecutions(limit));
                setLoading(false);
              }, 500);
            }}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
              <Zap size={12} />
              <span>Total</span>
            </div>
            <span className="text-lg font-mono font-semibold text-slate-200">
              {stats.total}
            </span>
          </div>
          <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
            <div className="flex items-center gap-2 text-xs text-emerald-500 mb-1">
              <CheckCircle size={12} />
              <span>Success</span>
            </div>
            <span className="text-lg font-mono font-semibold text-emerald-400">
              {stats.success}
            </span>
          </div>
          <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
            <div className="flex items-center gap-2 text-xs text-red-500 mb-1">
              <XCircle size={12} />
              <span>Errors</span>
            </div>
            <span className="text-lg font-mono font-semibold text-red-400">
              {stats.error}
            </span>
          </div>
          <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
            <div className="flex items-center gap-2 text-xs text-cyan-500 mb-1">
              <Clock size={12} />
              <span>Avg Time</span>
            </div>
            <span className="text-lg font-mono font-semibold text-cyan-400">
              {stats.avgTime}ms
            </span>
          </div>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <Filter size={12} className="text-slate-500" />
          <div className="flex items-center gap-1 bg-slate-800/30 rounded-lg p-1">
            {(["all", "success", "error"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  "px-3 py-1 rounded text-xs font-mono transition-colors",
                  filter === f
                    ? f === "all"
                      ? "bg-slate-700 text-cyan-400"
                      : f === "success"
                      ? "bg-slate-700 text-emerald-400"
                      : "bg-slate-700 text-red-400"
                    : "text-slate-500 hover:text-slate-300"
                )}
              >
                {f === "all" ? "All" : f === "success" ? "Success" : "Errors"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Execution list */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-3 text-slate-500">
              <Loader2 size={24} className="animate-spin text-cyan-400" />
              <span className="text-xs font-mono">Loading history...</span>
            </div>
          </div>
        ) : filteredExecutions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <History size={48} className="opacity-20 mb-4" />
            <p className="text-sm font-mono">No executions found</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredExecutions.map((execution) => (
              <ExecutionItem key={execution.id} execution={execution} />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 p-3 border-t border-slate-800 bg-slate-900/30">
        <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
          <span>Showing {filteredExecutions.length} executions</span>
          <span>
            {((stats.success / stats.total) * 100 || 0).toFixed(1)}% success rate
          </span>
        </div>
      </div>
    </div>
  );
}
