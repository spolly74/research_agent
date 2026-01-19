/**
 * PlanViewer - Displays the orchestrator's research plan
 * Terminal-style collapsible list with task status indicators
 */

import { useState } from "react";
import { cn } from "../../lib/utils";
import type { Plan, PlanTask } from "../../api/status";
import { AgentBadge } from "./AgentIndicator";
import { ChevronDown, ChevronRight, Target, CheckCircle2, Circle, Loader2 } from "lucide-react";

interface PlanViewerProps {
  plan: Plan | null;
  className?: string;
  defaultExpanded?: boolean;
}

const TASK_STATUS_ICONS: Record<string, { icon: React.ReactNode; color: string }> = {
  pending: {
    icon: <Circle size={12} />,
    color: "text-slate-500",
  },
  in_progress: {
    icon: <Loader2 size={12} className="animate-spin" />,
    color: "text-cyan-400",
  },
  completed: {
    icon: <CheckCircle2 size={12} />,
    color: "text-emerald-400",
  },
  failed: {
    icon: <Circle size={12} />,
    color: "text-red-400",
  },
};

function TaskItem({ task, index }: { task: PlanTask; index: number }) {
  const status = TASK_STATUS_ICONS[task.status] || TASK_STATUS_ICONS.pending;

  return (
    <div
      className={cn(
        "group flex items-start gap-3 p-2 rounded transition-colors",
        task.status === "in_progress" && "bg-cyan-500/5 border-l-2 border-cyan-500",
        task.status === "completed" && "opacity-60"
      )}
    >
      {/* Task number */}
      <div className="flex-shrink-0 w-5 h-5 rounded bg-slate-800 border border-slate-700 flex items-center justify-center">
        <span className="text-[10px] font-mono text-slate-500">{index + 1}</span>
      </div>

      {/* Status icon */}
      <div className={cn("flex-shrink-0 mt-0.5", status.color)}>{status.icon}</div>

      {/* Task details */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p
            className={cn(
              "text-sm leading-tight",
              task.status === "completed" ? "text-slate-500 line-through" : "text-slate-300"
            )}
          >
            {task.description}
          </p>
        </div>

        {/* Agent assignment */}
        <div className="mt-1.5">
          <AgentBadge agentName={task.assigned_agent} />
        </div>

        {/* Dependencies */}
        {task.dependencies && task.dependencies.length > 0 && (
          <div className="mt-1 text-[10px] font-mono text-slate-600">
            depends on: {task.dependencies.join(", ")}
          </div>
        )}
      </div>
    </div>
  );
}

export function PlanViewer({ plan, className, defaultExpanded = true }: PlanViewerProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!plan) {
    return (
      <div className={cn("rounded-lg bg-slate-800/30 border border-slate-700/50 p-4", className)}>
        <div className="flex items-center gap-2 text-slate-500">
          <Target size={16} className="opacity-50" />
          <span className="font-mono text-sm">Awaiting plan generation...</span>
        </div>
        <div className="mt-3 space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-8 rounded bg-slate-800/50 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const completedTasks = plan.tasks.filter((t) => t.status === "completed").length;
  const totalTasks = plan.tasks.length;
  const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  return (
    <div
      className={cn(
        "rounded-lg bg-slate-800/30 border border-slate-700/50 overflow-hidden",
        className
      )}
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown size={14} className="text-slate-500" />
          ) : (
            <ChevronRight size={14} className="text-slate-500" />
          )}
          <Target size={14} className="text-cyan-500" />
          <span className="font-mono text-sm text-slate-300">RESEARCH PLAN</span>
        </div>

        <div className="flex items-center gap-3">
          {/* Task counter */}
          <span className="text-xs font-mono text-slate-500">
            {completedTasks}/{totalTasks} tasks
          </span>

          {/* Mini progress */}
          <div className="w-16 h-1.5 rounded-full bg-slate-700 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="border-t border-slate-700/50">
          {/* Main goal */}
          <div className="px-3 py-2 bg-slate-800/50 border-b border-slate-700/30">
            <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1">
              Objective
            </div>
            <p className="text-sm text-slate-200">{plan.main_goal}</p>

            {/* Scope info */}
            {plan.scope && (
              <div className="mt-2 flex items-center gap-3 text-[10px] font-mono text-slate-500">
                <span className="px-1.5 py-0.5 rounded bg-slate-700/50 border border-slate-600/50">
                  {plan.scope.scope.toUpperCase()}
                </span>
                <span>{plan.scope.target_pages} pages</span>
                <span>~{plan.scope.target_word_count.toLocaleString()} words</span>
              </div>
            )}
          </div>

          {/* Task list */}
          <div className="p-2 space-y-1 max-h-64 overflow-y-auto">
            {plan.tasks.map((task, index) => (
              <TaskItem key={task.id} task={task} index={index} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
