/**
 * PlanApprovalModal - Modal for reviewing and approving research plans
 * Shows when the orchestrator generates a plan and awaits user approval
 */

import { useState } from "react";
import { cn } from "../../lib/utils";
import type { Plan, PlanTask } from "../../api/status";
import { approvePlan } from "../../api/status";
import { PlanEditor } from "./PlanEditor";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Target,
  Edit3,
  Loader2,
  Sparkles,
} from "lucide-react";

interface PlanApprovalModalProps {
  sessionId: string;
  plan: Plan;
  isOpen: boolean;
  onApproved: () => void;
  onRejected: () => void;
  onClose: () => void;
}

export function PlanApprovalModal({
  sessionId,
  plan,
  isOpen,
  onApproved,
  onRejected,
  onClose,
}: PlanApprovalModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedPlan, setEditedPlan] = useState<Plan>(plan);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleApprove = async () => {
    setIsSubmitting(true);
    setError(null);

    const isModified = JSON.stringify(plan) !== JSON.stringify(editedPlan);

    const result = await approvePlan(sessionId, {
      approved: true,
      modifications: isModified ? { main_goal: editedPlan.main_goal, tasks: editedPlan.tasks } : undefined,
    });

    setIsSubmitting(false);

    if (result) {
      onApproved();
      onClose();
    } else {
      setError("Failed to approve plan. Please try again.");
    }
  };

  const handleReject = async () => {
    setIsSubmitting(true);
    setError(null);

    const result = await approvePlan(sessionId, {
      approved: false,
    });

    setIsSubmitting(false);

    if (result) {
      onRejected();
      onClose();
    } else {
      setError("Failed to reject plan. Please try again.");
    }
  };

  const handlePlanUpdated = (updatedPlan: Plan) => {
    setEditedPlan(updatedPlan);
  };

  const taskCount = editedPlan.tasks.length;
  const agentCount = new Set(editedPlan.tasks.map((t) => t.assigned_agent)).size;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/90 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-3xl max-h-[90vh] mx-4 bg-slate-900 rounded-xl border border-slate-700/50 shadow-2xl shadow-cyan-500/10 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-slate-700/50 bg-gradient-to-r from-slate-900 to-slate-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
                <Target size={20} className="text-cyan-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-100">
                  Review Research Plan
                </h2>
                <p className="text-sm text-slate-400 mt-0.5">
                  Review and approve the plan before execution begins
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsEditing(!isEditing)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all",
                  isEditing
                    ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                    : "bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700"
                )}
              >
                <Edit3 size={14} />
                <span>{isEditing ? "Editing" : "Edit"}</span>
              </button>
            </div>
          </div>

          {/* Stats bar */}
          <div className="mt-4 flex items-center gap-6">
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <Sparkles size={12} className="text-cyan-400" />
              <span className="text-slate-300">{taskCount} tasks</span>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-slate-300">{agentCount} agents</span>
            </div>
            {editedPlan.scope && (
              <>
                <div className="text-xs font-mono text-slate-500">
                  <span className="text-slate-300">{editedPlan.scope.target_pages}</span> pages
                </div>
                <div className="text-xs font-mono text-slate-500">
                  <span className="text-slate-300">{editedPlan.scope.target_word_count.toLocaleString()}</span> words
                </div>
              </>
            )}
          </div>
        </div>

        {/* Plan content - scrollable */}
        <div className="flex-1 overflow-y-auto p-5">
          {/* Objective */}
          <div className="mb-5 p-4 rounded-lg bg-slate-800/50 border border-slate-700/50">
            <label className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
              Research Objective
            </label>
            <p className="mt-1 text-slate-200">{editedPlan.main_goal}</p>
          </div>

          {/* Plan editor */}
          <PlanEditor
            sessionId={sessionId}
            plan={editedPlan}
            isEditable={isEditing}
            onPlanUpdated={handlePlanUpdated}
          />
        </div>

        {/* Error message */}
        {error && (
          <div className="mx-5 mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-2 text-red-400 text-sm">
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Footer */}
        <div className="p-5 border-t border-slate-700/50 bg-slate-900/50">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              {isEditing ? (
                <span className="text-cyan-400">
                  Make changes above, then approve or reject the plan
                </span>
              ) : (
                "You can edit the plan before approving"
              )}
            </p>

            <div className="flex items-center gap-3">
              <button
                onClick={handleReject}
                disabled={isSubmitting}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-300 hover:text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <XCircle size={16} className="text-red-400" />
                )}
                <span>Reject</span>
              </button>

              <button
                onClick={handleApprove}
                disabled={isSubmitting}
                className="flex items-center gap-2 px-5 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white text-sm font-medium shadow-lg shadow-cyan-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <CheckCircle size={16} />
                )}
                <span>Approve & Execute</span>
              </button>
            </div>
          </div>
        </div>

        {/* Decorative elements */}
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />
      </div>
    </div>
  );
}
