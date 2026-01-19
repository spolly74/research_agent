/**
 * ToolCard - Individual tool display with actions
 * Shows tool info, status, and allows management actions
 */

import { useState } from "react";
import { cn } from "../../lib/utils";
import {
  type ToolSummary,
  type ToolStatus,
  CATEGORY_INFO,
  STATUS_INFO,
  updateToolStatus,
  deleteTool,
  executeTool,
} from "../../api/tools";
import {
  Wrench,
  Play,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Shield,
  Zap,
  Clock,
  Users,
  ChevronDown,
  ChevronUp,
  Loader2,
  CheckCircle,
  XCircle,
  AlertTriangle,
} from "lucide-react";

interface ToolCardProps {
  tool: ToolSummary;
  onStatusChange?: () => void;
  onDelete?: () => void;
  className?: string;
}

export function ToolCard({ tool, onStatusChange, onDelete, className }: ToolCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const categoryInfo = CATEGORY_INFO[tool.category];
  const statusInfo = STATUS_INFO[tool.status];

  const handleToggleStatus = async () => {
    setLoading("status");
    try {
      const newStatus: ToolStatus = tool.status === "active" ? "disabled" : "active";
      await updateToolStatus(tool.name, newStatus);
      onStatusChange?.();
    } catch (error) {
      console.error("Failed to update status:", error);
    } finally {
      setLoading(null);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete "${tool.name}"?`)) return;

    setLoading("delete");
    try {
      await deleteTool(tool.name);
      onDelete?.();
    } catch (error) {
      console.error("Failed to delete tool:", error);
    } finally {
      setLoading(null);
    }
  };

  const handleTest = async () => {
    setLoading("test");
    setTestResult(null);
    try {
      const result = await executeTool(tool.name, {});
      setTestResult({
        success: result.success,
        message: result.success
          ? `Executed in ${result.execution_time_ms}ms`
          : result.error || "Unknown error",
      });
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : "Test failed",
      });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div
      className={cn(
        "bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden transition-all duration-200",
        expanded && "ring-1 ring-cyan-500/30",
        className
      )}
    >
      {/* Header */}
      <div
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-slate-800/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Icon */}
        <div
          className={cn(
            "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
            categoryInfo.bgColor
          )}
        >
          <Wrench size={18} className={categoryInfo.color} />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-mono font-semibold text-slate-200 truncate">
              {tool.name}
            </h3>
            {tool.is_builtin && (
              <Shield size={12} className="text-slate-500 flex-shrink-0" title="Built-in tool" />
            )}
          </div>
          <p className="text-xs text-slate-500 truncate">{tool.description}</p>
        </div>

        {/* Category badge */}
        <span
          className={cn(
            "px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider flex-shrink-0",
            categoryInfo.bgColor,
            categoryInfo.color
          )}
        >
          {categoryInfo.label}
        </span>

        {/* Status */}
        <span
          className={cn(
            "px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider flex-shrink-0",
            statusInfo.bgColor,
            statusInfo.color
          )}
        >
          {statusInfo.label}
        </span>

        {/* Expand icon */}
        <div className="text-slate-500">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-slate-800 p-4 space-y-4 bg-slate-950/30">
          {/* Stats row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-2 text-sm">
              <Zap size={14} className="text-amber-400" />
              <span className="text-slate-400">Executions:</span>
              <span className="font-mono text-slate-200">{tool.execution_count}</span>
            </div>

            <div className="flex items-center gap-2 text-sm">
              <Users size={14} className="text-cyan-400" />
              <span className="text-slate-400">Agents:</span>
              <span className="font-mono text-slate-200">
                {tool.allowed_agents.length > 0 ? tool.allowed_agents.join(", ") : "All"}
              </span>
            </div>
          </div>

          {/* Test result */}
          {testResult && (
            <div
              className={cn(
                "flex items-center gap-2 p-3 rounded-lg text-sm",
                testResult.success
                  ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                  : "bg-red-500/10 border border-red-500/30 text-red-400"
              )}
            >
              {testResult.success ? (
                <CheckCircle size={14} />
              ) : (
                <XCircle size={14} />
              )}
              <span className="font-mono text-xs">{testResult.message}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
            {/* Test button */}
            <button
              onClick={handleTest}
              disabled={loading !== null || tool.status !== "active"}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                "bg-cyan-500/10 border border-cyan-500/30 text-cyan-400",
                "hover:bg-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {loading === "test" ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Play size={12} />
              )}
              <span>Test</span>
            </button>

            {/* Toggle status */}
            <button
              onClick={handleToggleStatus}
              disabled={loading !== null}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                tool.status === "active"
                  ? "bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20"
                  : "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {loading === "status" ? (
                <Loader2 size={12} className="animate-spin" />
              ) : tool.status === "active" ? (
                <ToggleRight size={12} />
              ) : (
                <ToggleLeft size={12} />
              )}
              <span>{tool.status === "active" ? "Disable" : "Enable"}</span>
            </button>

            {/* Delete (only for custom tools) */}
            {!tool.is_builtin && (
              <button
                onClick={handleDelete}
                disabled={loading !== null}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                  "bg-red-500/10 border border-red-500/30 text-red-400",
                  "hover:bg-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed",
                  "ml-auto"
                )}
              >
                {loading === "delete" ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Trash2 size={12} />
                )}
                <span>Delete</span>
              </button>
            )}
          </div>

          {/* Error message */}
          {tool.status === "error" && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30">
              <AlertTriangle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
              <span className="text-xs text-red-400 font-mono">Tool is in error state</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
