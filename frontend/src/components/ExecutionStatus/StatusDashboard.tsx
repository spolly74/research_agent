/**
 * StatusDashboard - Main container for execution status visualization
 * Mission Control themed with grid background and neon accents
 */

import { useState, useEffect, useCallback } from "react";
import { cn } from "../../lib/utils";
import { useExecutionStatus } from "../../hooks/useExecutionStatus";
import { PhaseIndicator, PhaseRow } from "./PhaseIndicator";
import { ProgressTimeline } from "./ProgressTimeline";
import { AgentIndicator } from "./AgentIndicator";
import { PlanViewer } from "./PlanViewer";
import { PlanEditor } from "./PlanEditor";
import { PlanApprovalModal } from "./PlanApprovalModal";
import { ToolActivity } from "./ToolActivity";
import type { Plan } from "../../api/status";
import {
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Edit3,
} from "lucide-react";

interface StatusDashboardProps {
  sessionId: string | null;
  isProcessing?: boolean;
  className?: string;
}

const PHASES = [
  "initializing",
  "planning",
  "researching",
  "reviewing",
  "coding",
  "editing",
  "finalizing",
];

export function StatusDashboard({
  sessionId,
  isProcessing = false,
  className,
}: StatusDashboardProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showDetails, setShowDetails] = useState(true);
  const [isEditingPlan, setIsEditingPlan] = useState(false);
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [localPlan, setLocalPlan] = useState<Plan | null>(null);

  const {
    status,
    progress,
    plan,
    activityLog,
    isConnected,
    isLoading,
    error,
    refresh,
  } = useExecutionStatus(sessionId);

  // Keep local plan in sync with fetched plan
  useEffect(() => {
    if (plan && !localPlan) {
      setLocalPlan(plan);
    }
  }, [plan, localPlan]);

  // Auto-show approval modal when plan is waiting for approval
  useEffect(() => {
    if (status?.plan_waiting_approval && plan && !showApprovalModal) {
      setShowApprovalModal(true);
    }
  }, [status?.plan_waiting_approval, plan, showApprovalModal]);

  const handlePlanUpdated = useCallback((updatedPlan: Plan) => {
    setLocalPlan(updatedPlan);
  }, []);

  const handlePlanApproved = useCallback(() => {
    setShowApprovalModal(false);
    setIsEditingPlan(false);
    refresh();
  }, [refresh]);

  const handlePlanRejected = useCallback(() => {
    setShowApprovalModal(false);
  }, []);

  // Don't render if no session or not processing
  if (!sessionId || (!isProcessing && !status)) {
    return null;
  }

  const currentPhase = status?.current_phase || "initializing";
  const isCompleted = currentPhase === "completed";
  const hasError = currentPhase === "error" || !!error;
  const displayPlan = localPlan || plan;

  return (
    <div
      className={cn(
        "rounded-xl overflow-hidden transition-all duration-500",
        "bg-gradient-to-b from-slate-900/95 to-slate-950/95",
        "border border-slate-700/50",
        "backdrop-blur-sm",
        "shadow-2xl shadow-slate-900/50",
        className
      )}
    >
      {/* Grid background effect */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-5">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `
              linear-gradient(rgba(99, 102, 241, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(99, 102, 241, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: "20px 20px",
          }}
        />
      </div>

      {/* Header */}
      <div className="relative px-4 py-3 border-b border-slate-700/50 bg-slate-800/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Status indicator */}
            <div className="relative">
              <div
                className={cn(
                  "w-3 h-3 rounded-full",
                  isCompleted && "bg-emerald-500",
                  hasError && "bg-red-500",
                  !isCompleted && !hasError && "bg-cyan-500 animate-pulse"
                )}
              />
              {!isCompleted && !hasError && (
                <div className="absolute inset-0 rounded-full bg-cyan-500 animate-ping opacity-50" />
              )}
            </div>

            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-semibold text-slate-200">
                  EXECUTION STATUS
                </span>
                {isCompleted && (
                  <CheckCircle2 size={14} className="text-emerald-500" />
                )}
                {hasError && (
                  <AlertTriangle size={14} className="text-red-500" />
                )}
              </div>
              <div className="text-[10px] font-mono text-slate-500">
                {sessionId}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Current phase badge */}
            <PhaseIndicator phase={currentPhase} isActive={!isCompleted && !hasError} />

            {/* Refresh button */}
            <button
              onClick={refresh}
              disabled={isLoading}
              className={cn(
                "p-1.5 rounded-lg transition-colors",
                "hover:bg-slate-700/50 text-slate-400 hover:text-slate-200",
                isLoading && "animate-spin"
              )}
            >
              <RefreshCw size={14} />
            </button>

            {/* Toggle expand */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 rounded-lg hover:bg-slate-700/50 text-slate-400 hover:text-slate-200 transition-colors"
            >
              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          </div>
        </div>

        {/* Phase progress row */}
        <div className="mt-3">
          <PhaseRow phases={PHASES} currentPhase={currentPhase} />
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="relative p-4 space-y-4">
          {/* Progress timeline */}
          {progress && (
            <ProgressTimeline
              progress={progress.overall_progress}
              phases={progress.phases}
            />
          )}

          {/* Error display */}
          {(hasError || error) && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30">
              <div className="flex items-center gap-2 text-red-400">
                <AlertTriangle size={14} />
                <span className="font-mono text-sm">Error</span>
              </div>
              <p className="mt-1 text-sm text-red-300/80">
                {error || status?.error || "An unknown error occurred"}
              </p>
            </div>
          )}

          {/* Show/hide details toggle */}
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center gap-1 text-xs font-mono text-slate-500 hover:text-slate-300 transition-colors"
          >
            <Activity size={12} />
            <span>{showDetails ? "Hide" : "Show"} Details</span>
            {showDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>

          {showDetails && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Left column */}
              <div className="space-y-4">
                {/* Active agent */}
                <AgentIndicator
                  agentName={status?.active_agent || null}
                  tools={status?.active_tools || []}
                  progress={status?.progress}
                />

                {/* Plan viewer/editor with toggle */}
                <div className="space-y-2">
                  {displayPlan && (
                    <div className="flex items-center justify-end">
                      <button
                        onClick={() => setIsEditingPlan(!isEditingPlan)}
                        className={cn(
                          "flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium transition-all",
                          isEditingPlan
                            ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                            : "bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700"
                        )}
                      >
                        <Edit3 size={12} />
                        <span>{isEditingPlan ? "Editing" : "Edit Plan"}</span>
                      </button>
                    </div>
                  )}

                  {isEditingPlan ? (
                    <PlanEditor
                      sessionId={sessionId}
                      plan={displayPlan}
                      isEditable={true}
                      onPlanUpdated={handlePlanUpdated}
                    />
                  ) : (
                    <PlanViewer plan={displayPlan} defaultExpanded={true} />
                  )}
                </div>
              </div>

              {/* Right column */}
              <div>
                {/* Activity log */}
                <ToolActivity
                  entries={activityLog}
                  isConnected={isConnected}
                  maxHeight="300px"
                />
              </div>
            </div>
          )}

          {/* Completed state */}
          {isCompleted && (
            <div className="text-center py-4">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                <CheckCircle2 size={16} className="text-emerald-400" />
                <span className="font-mono text-sm text-emerald-400">
                  Research Complete
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Plan Approval Modal */}
      {displayPlan && (
        <PlanApprovalModal
          sessionId={sessionId}
          plan={displayPlan}
          isOpen={showApprovalModal}
          onApproved={handlePlanApproved}
          onRejected={handlePlanRejected}
          onClose={() => setShowApprovalModal(false)}
        />
      )}
    </div>
  );
}

export { PhaseIndicator, PhaseRow } from "./PhaseIndicator";
export { ProgressTimeline, MiniProgress } from "./ProgressTimeline";
export { AgentIndicator, AgentBadge } from "./AgentIndicator";
export { PlanViewer } from "./PlanViewer";
export { PlanEditor } from "./PlanEditor";
export { PlanApprovalModal } from "./PlanApprovalModal";
export { ToolActivity, CompactActivity } from "./ToolActivity";
