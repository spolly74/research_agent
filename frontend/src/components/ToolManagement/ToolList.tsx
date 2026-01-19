/**
 * ToolList - Display all registered tools with filtering
 * Shows tools organized by category with search and status filters
 */

import { useState, useEffect, useMemo } from "react";
import { cn } from "../../lib/utils";
import {
  listTools,
  type ToolRegistryStatus,
  type ToolCategory,
  type ToolStatus,
  CATEGORY_INFO,
  STATUS_INFO,
} from "../../api/tools";
import { ToolCard } from "./ToolCard";
import {
  Search,
  Filter,
  Wrench,
  Package,
  Sparkles,
  AlertCircle,
  Loader2,
  RefreshCw,
  Grid3X3,
  List,
  Zap,
} from "lucide-react";

interface ToolListProps {
  onCreateClick?: () => void;
  className?: string;
}

type ViewMode = "grid" | "list";

export function ToolList({ onCreateClick, className }: ToolListProps) {
  const [registry, setRegistry] = useState<ToolRegistryStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<ToolCategory | "all">("all");
  const [statusFilter, setStatusFilter] = useState<ToolStatus | "all">("all");
  const [showBuiltinOnly, setShowBuiltinOnly] = useState<boolean | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("list");

  const loadTools = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listTools();
      setRegistry(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tools");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTools();
  }, []);

  // Filtered tools
  const filteredTools = useMemo(() => {
    if (!registry) return [];

    return registry.tools.filter((tool) => {
      // Search filter
      if (search) {
        const searchLower = search.toLowerCase();
        if (
          !tool.name.toLowerCase().includes(searchLower) &&
          !tool.description.toLowerCase().includes(searchLower)
        ) {
          return false;
        }
      }

      // Category filter
      if (categoryFilter !== "all" && tool.category !== categoryFilter) {
        return false;
      }

      // Status filter
      if (statusFilter !== "all" && tool.status !== statusFilter) {
        return false;
      }

      // Builtin filter
      if (showBuiltinOnly === true && !tool.is_builtin) {
        return false;
      }
      if (showBuiltinOnly === false && tool.is_builtin) {
        return false;
      }

      return true;
    });
  }, [registry, search, categoryFilter, statusFilter, showBuiltinOnly]);

  // Stats
  const stats = useMemo(() => {
    if (!registry) return null;
    return {
      total: registry.total_tools,
      active: registry.active_tools,
      builtin: registry.builtin_tools,
      custom: registry.custom_tools,
      totalExecutions: registry.tools.reduce((sum, t) => sum + t.execution_count, 0),
    };
  }, [registry]);

  const categories: (ToolCategory | "all")[] = ["all", "browser", "api", "math", "code", "data", "file", "custom"];
  const statuses: (ToolStatus | "all")[] = ["all", "active", "disabled", "error"];

  if (loading) {
    return (
      <div className={cn("flex items-center justify-center p-12", className)}>
        <div className="flex flex-col items-center gap-3 text-slate-500">
          <Loader2 size={32} className="animate-spin text-cyan-400" />
          <span className="text-sm font-mono">Loading tools...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("flex items-center justify-center p-12", className)}>
        <div className="flex flex-col items-center gap-3 text-red-400">
          <AlertCircle size={32} />
          <span className="text-sm font-mono">{error}</span>
          <button
            onClick={loadTools}
            className="px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-sm hover:bg-red-500/20 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-slate-800 bg-slate-900/50">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 flex items-center justify-center">
              <Wrench size={20} className="text-cyan-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-200">Tool Registry</h2>
              <p className="text-xs text-slate-500 font-mono">
                {stats?.total} tools registered
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Refresh */}
            <button
              onClick={loadTools}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              title="Refresh"
            >
              <RefreshCw size={16} />
            </button>

            {/* View mode toggle */}
            <div className="flex items-center bg-slate-800/50 rounded-lg p-1">
              <button
                onClick={() => setViewMode("list")}
                className={cn(
                  "p-1.5 rounded transition-colors",
                  viewMode === "list"
                    ? "bg-slate-700 text-cyan-400"
                    : "text-slate-500 hover:text-slate-300"
                )}
              >
                <List size={14} />
              </button>
              <button
                onClick={() => setViewMode("grid")}
                className={cn(
                  "p-1.5 rounded transition-colors",
                  viewMode === "grid"
                    ? "bg-slate-700 text-cyan-400"
                    : "text-slate-500 hover:text-slate-300"
                )}
              >
                <Grid3X3 size={14} />
              </button>
            </div>

            {/* Create button */}
            {onCreateClick && (
              <button
                onClick={onCreateClick}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gradient-to-r from-cyan-600/20 to-blue-600/20 border border-cyan-500/30 text-cyan-400 text-sm font-medium hover:from-cyan-600/30 hover:to-blue-600/30 transition-all"
              >
                <Sparkles size={14} />
                <span>Create Tool</span>
              </button>
            )}
          </div>
        </div>

        {/* Stats cards */}
        {stats && (
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
              <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                <Package size={12} />
                <span>Built-in</span>
              </div>
              <span className="text-lg font-mono font-semibold text-slate-200">
                {stats.builtin}
              </span>
            </div>
            <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
              <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
                <Sparkles size={12} />
                <span>Custom</span>
              </div>
              <span className="text-lg font-mono font-semibold text-slate-200">
                {stats.custom}
              </span>
            </div>
            <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
              <div className="flex items-center gap-2 text-xs text-emerald-500 mb-1">
                <Wrench size={12} />
                <span>Active</span>
              </div>
              <span className="text-lg font-mono font-semibold text-emerald-400">
                {stats.active}
              </span>
            </div>
            <div className="bg-slate-800/30 rounded-lg p-3 border border-slate-700/50">
              <div className="flex items-center gap-2 text-xs text-amber-500 mb-1">
                <Zap size={12} />
                <span>Executions</span>
              </div>
              <span className="text-lg font-mono font-semibold text-amber-400">
                {stats.totalExecutions.toLocaleString()}
              </span>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search tools..."
              className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg py-2 pl-9 pr-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 focus:border-cyan-500/50"
            />
          </div>

          {/* Category filter */}
          <div className="flex items-center gap-1 bg-slate-800/30 rounded-lg p-1">
            <Filter size={12} className="text-slate-500 ml-2" />
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategoryFilter(cat)}
                className={cn(
                  "px-2 py-1 rounded text-xs font-mono transition-colors",
                  categoryFilter === cat
                    ? "bg-slate-700 text-cyan-400"
                    : "text-slate-500 hover:text-slate-300"
                )}
              >
                {cat === "all" ? "All" : CATEGORY_INFO[cat].label}
              </button>
            ))}
          </div>

          {/* Status filter */}
          <div className="flex items-center gap-1 bg-slate-800/30 rounded-lg p-1">
            {statuses.map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={cn(
                  "px-2 py-1 rounded text-xs font-mono transition-colors",
                  statusFilter === status
                    ? status === "all"
                      ? "bg-slate-700 text-cyan-400"
                      : `bg-slate-700 ${STATUS_INFO[status].color}`
                    : "text-slate-500 hover:text-slate-300"
                )}
              >
                {status === "all" ? "Any" : STATUS_INFO[status].label}
              </button>
            ))}
          </div>

          {/* Builtin toggle */}
          <div className="flex items-center gap-1 bg-slate-800/30 rounded-lg p-1">
            <button
              onClick={() => setShowBuiltinOnly(showBuiltinOnly === true ? null : true)}
              className={cn(
                "px-2 py-1 rounded text-xs font-mono transition-colors",
                showBuiltinOnly === true
                  ? "bg-slate-700 text-cyan-400"
                  : "text-slate-500 hover:text-slate-300"
              )}
            >
              Built-in
            </button>
            <button
              onClick={() => setShowBuiltinOnly(showBuiltinOnly === false ? null : false)}
              className={cn(
                "px-2 py-1 rounded text-xs font-mono transition-colors",
                showBuiltinOnly === false
                  ? "bg-slate-700 text-cyan-400"
                  : "text-slate-500 hover:text-slate-300"
              )}
            >
              Custom
            </button>
          </div>
        </div>
      </div>

      {/* Tool list */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredTools.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Wrench size={48} className="opacity-20 mb-4" />
            <p className="text-sm font-mono">No tools match your filters</p>
          </div>
        ) : viewMode === "list" ? (
          <div className="space-y-3">
            {filteredTools.map((tool) => (
              <ToolCard
                key={tool.name}
                tool={tool}
                onStatusChange={loadTools}
                onDelete={loadTools}
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {filteredTools.map((tool) => (
              <ToolCard
                key={tool.name}
                tool={tool}
                onStatusChange={loadTools}
                onDelete={loadTools}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 p-3 border-t border-slate-800 bg-slate-900/30">
        <div className="flex items-center justify-between text-xs text-slate-500 font-mono">
          <span>
            Showing {filteredTools.length} of {registry?.total_tools || 0} tools
          </span>
          <span>
            {filteredTools.filter((t) => t.status === "active").length} active
          </span>
        </div>
      </div>
    </div>
  );
}
