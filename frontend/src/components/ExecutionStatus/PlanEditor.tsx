/**
 * PlanEditor - Editable plan visualization with task management
 * Allows adding, editing, removing, and reordering tasks
 */

import { useState, useCallback } from "react";
import { cn } from "../../lib/utils";
import type { Plan, PlanTask, TaskCreate, TaskUpdate } from "../../api/status";
import { updatePlanTask, addPlanTask, removePlanTask, reorderPlanTasks } from "../../api/status";
import { AgentBadge } from "./AgentIndicator";
import {
  Target,
  CheckCircle2,
  Circle,
  Loader2,
  Plus,
  Trash2,
  GripVertical,
  Edit3,
  Save,
  X,
  ChevronUp,
  ChevronDown,
  AlertCircle,
} from "lucide-react";

// Available agents for assignment
const AVAILABLE_AGENTS = [
  { id: "researcher", label: "Researcher" },
  { id: "reviewer", label: "Reviewer" },
  { id: "coder", label: "Coder" },
  { id: "editor", label: "Editor" },
];

interface PlanEditorProps {
  sessionId: string;
  plan: Plan | null;
  isEditable?: boolean;
  onPlanUpdated?: (plan: Plan) => void;
  className?: string;
}

interface EditableTaskProps {
  task: PlanTask;
  index: number;
  totalTasks: number;
  sessionId: string;
  isEditable: boolean;
  onTaskUpdated: (task: PlanTask) => void;
  onTaskRemoved: (taskId: number) => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

const TASK_STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  pending: {
    icon: <Circle size={14} />,
    color: "text-slate-500 border-slate-600",
    label: "Pending",
  },
  in_progress: {
    icon: <Loader2 size={14} className="animate-spin" />,
    color: "text-cyan-400 border-cyan-500",
    label: "In Progress",
  },
  completed: {
    icon: <CheckCircle2 size={14} />,
    color: "text-emerald-400 border-emerald-500",
    label: "Completed",
  },
  failed: {
    icon: <AlertCircle size={14} />,
    color: "text-red-400 border-red-500",
    label: "Failed",
  },
};

function EditableTask({
  task,
  index,
  totalTasks,
  sessionId,
  isEditable,
  onTaskUpdated,
  onTaskRemoved,
  onMoveUp,
  onMoveDown,
}: EditableTaskProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedDescription, setEditedDescription] = useState(task.description);
  const [editedAgent, setEditedAgent] = useState(task.assigned_agent);
  const [isSaving, setIsSaving] = useState(false);

  const statusConfig = TASK_STATUS_CONFIG[task.status] || TASK_STATUS_CONFIG.pending;

  const handleSave = async () => {
    setIsSaving(true);
    const updates: TaskUpdate = {};

    if (editedDescription !== task.description) {
      updates.description = editedDescription;
    }
    if (editedAgent !== task.assigned_agent) {
      updates.assigned_agent = editedAgent;
    }

    if (Object.keys(updates).length > 0) {
      const updatedTask = await updatePlanTask(sessionId, task.id, updates);
      if (updatedTask) {
        onTaskUpdated(updatedTask);
      }
    }

    setIsSaving(false);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedDescription(task.description);
    setEditedAgent(task.assigned_agent);
    setIsEditing(false);
  };

  const handleRemove = async () => {
    if (window.confirm("Remove this task from the plan?")) {
      const success = await removePlanTask(sessionId, task.id);
      if (success) {
        onTaskRemoved(task.id);
      }
    }
  };

  return (
    <div
      className={cn(
        "group relative rounded-lg border transition-all duration-200",
        task.status === "in_progress"
          ? "bg-cyan-500/5 border-cyan-500/30"
          : task.status === "completed"
          ? "bg-slate-800/30 border-slate-700/30 opacity-70"
          : "bg-slate-800/50 border-slate-700/50 hover:border-slate-600/50"
      )}
    >
      {/* Task number indicator */}
      <div className="absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-slate-900 border border-slate-700 flex items-center justify-center">
        <span className="text-[10px] font-mono font-bold text-slate-400">{index + 1}</span>
      </div>

      <div className="pl-6 pr-3 py-3">
        {isEditing ? (
          /* Edit Mode */
          <div className="space-y-3">
            <textarea
              value={editedDescription}
              onChange={(e) => setEditedDescription(e.target.value)}
              className="w-full bg-slate-900 border border-slate-600 rounded-lg p-2 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none resize-none"
              rows={2}
              placeholder="Task description..."
            />

            <div className="flex items-center gap-3">
              <select
                value={editedAgent}
                onChange={(e) => setEditedAgent(e.target.value)}
                className="bg-slate-900 border border-slate-600 rounded-lg px-2 py-1.5 text-xs font-mono text-slate-300 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none"
              >
                {AVAILABLE_AGENTS.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.label}
                  </option>
                ))}
              </select>

              <div className="flex-1" />

              <button
                onClick={handleCancel}
                className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
              >
                <X size={14} />
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-1 px-2 py-1 rounded bg-cyan-600/20 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-600/30 transition-colors text-xs font-medium disabled:opacity-50"
              >
                {isSaving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                <span>Save</span>
              </button>
            </div>
          </div>
        ) : (
          /* View Mode */
          <div className="flex items-start gap-3">
            {/* Status icon */}
            <div className={cn("flex-shrink-0 mt-0.5 p-1 rounded border", statusConfig.color)}>
              {statusConfig.icon}
            </div>

            {/* Task content */}
            <div className="flex-1 min-w-0">
              <p
                className={cn(
                  "text-sm leading-relaxed",
                  task.status === "completed" ? "text-slate-500 line-through" : "text-slate-200"
                )}
              >
                {task.description}
              </p>

              <div className="mt-2 flex items-center gap-3">
                <AgentBadge agentName={task.assigned_agent} />

                {task.dependencies && task.dependencies.length > 0 && (
                  <span className="text-[10px] font-mono text-slate-600">
                    depends: [{task.dependencies.join(", ")}]
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            {isEditable && (
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {/* Reorder buttons */}
                <div className="flex flex-col">
                  <button
                    onClick={onMoveUp}
                    disabled={index === 0}
                    className="p-0.5 text-slate-500 hover:text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronUp size={14} />
                  </button>
                  <button
                    onClick={onMoveDown}
                    disabled={index === totalTasks - 1}
                    className="p-0.5 text-slate-500 hover:text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronDown size={14} />
                  </button>
                </div>

                <button
                  onClick={() => setIsEditing(true)}
                  className="p-1.5 rounded hover:bg-slate-700 text-slate-500 hover:text-cyan-400 transition-colors"
                  title="Edit task"
                >
                  <Edit3 size={14} />
                </button>

                <button
                  onClick={handleRemove}
                  className="p-1.5 rounded hover:bg-slate-700 text-slate-500 hover:text-red-400 transition-colors"
                  title="Remove task"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function AddTaskForm({
  sessionId,
  onTaskAdded,
}: {
  sessionId: string;
  onTaskAdded: (task: PlanTask) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [description, setDescription] = useState("");
  const [agent, setAgent] = useState(AVAILABLE_AGENTS[0].id);
  const [isAdding, setIsAdding] = useState(false);

  const handleAdd = async () => {
    if (!description.trim()) return;

    setIsAdding(true);
    const taskCreate: TaskCreate = {
      description: description.trim(),
      assigned_agent: agent,
    };

    const newTask = await addPlanTask(sessionId, taskCreate);
    if (newTask) {
      onTaskAdded(newTask);
      setDescription("");
      setIsOpen(false);
    }
    setIsAdding(false);
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="w-full flex items-center justify-center gap-2 p-3 rounded-lg border border-dashed border-slate-700 hover:border-cyan-500/50 bg-slate-800/20 hover:bg-slate-800/40 text-slate-500 hover:text-cyan-400 transition-all"
      >
        <Plus size={16} />
        <span className="text-sm font-medium">Add Task</span>
      </button>
    );
  }

  return (
    <div className="p-4 rounded-lg border border-cyan-500/30 bg-slate-800/50 space-y-3">
      <div className="flex items-center gap-2 text-cyan-400 text-sm font-medium">
        <Plus size={14} />
        <span>New Task</span>
      </div>

      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        className="w-full bg-slate-900 border border-slate-600 rounded-lg p-2 text-sm text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none resize-none"
        rows={2}
        placeholder="Describe the task..."
        autoFocus
      />

      <div className="flex items-center gap-3">
        <label className="text-xs font-mono text-slate-500">Assign to:</label>
        <select
          value={agent}
          onChange={(e) => setAgent(e.target.value)}
          className="bg-slate-900 border border-slate-600 rounded-lg px-2 py-1.5 text-xs font-mono text-slate-300 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 focus:outline-none"
        >
          {AVAILABLE_AGENTS.map((a) => (
            <option key={a.id} value={a.id}>
              {a.label}
            </option>
          ))}
        </select>

        <div className="flex-1" />

        <button
          onClick={() => setIsOpen(false)}
          className="px-3 py-1.5 rounded text-slate-400 hover:text-slate-200 text-xs transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleAdd}
          disabled={!description.trim() || isAdding}
          className="flex items-center gap-1 px-3 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isAdding ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
          <span>Add</span>
        </button>
      </div>
    </div>
  );
}

export function PlanEditor({
  sessionId,
  plan,
  isEditable = false,
  onPlanUpdated,
  className,
}: PlanEditorProps) {
  const [localPlan, setLocalPlan] = useState<Plan | null>(plan);

  // Keep local plan in sync with prop
  if (plan !== localPlan && plan?.tasks?.length !== localPlan?.tasks?.length) {
    setLocalPlan(plan);
  }

  const handleTaskUpdated = useCallback(
    (updatedTask: PlanTask) => {
      if (!localPlan) return;

      const newPlan = {
        ...localPlan,
        tasks: localPlan.tasks.map((t) => (t.id === updatedTask.id ? updatedTask : t)),
      };
      setLocalPlan(newPlan);
      onPlanUpdated?.(newPlan);
    },
    [localPlan, onPlanUpdated]
  );

  const handleTaskRemoved = useCallback(
    (taskId: number) => {
      if (!localPlan) return;

      const newPlan = {
        ...localPlan,
        tasks: localPlan.tasks.filter((t) => t.id !== taskId),
      };
      setLocalPlan(newPlan);
      onPlanUpdated?.(newPlan);
    },
    [localPlan, onPlanUpdated]
  );

  const handleTaskAdded = useCallback(
    (newTask: PlanTask) => {
      if (!localPlan) return;

      const newPlan = {
        ...localPlan,
        tasks: [...localPlan.tasks, newTask],
      };
      setLocalPlan(newPlan);
      onPlanUpdated?.(newPlan);
    },
    [localPlan, onPlanUpdated]
  );

  const handleMoveTask = useCallback(
    async (fromIndex: number, toIndex: number) => {
      if (!localPlan) return;

      const tasks = [...localPlan.tasks];
      const [movedTask] = tasks.splice(fromIndex, 1);
      tasks.splice(toIndex, 0, movedTask);

      const newPlan = { ...localPlan, tasks };
      setLocalPlan(newPlan);

      // Update on server
      const taskOrder = tasks.map((t) => t.id);
      const updatedPlan = await reorderPlanTasks(sessionId, taskOrder);
      if (updatedPlan) {
        onPlanUpdated?.(updatedPlan);
      }
    },
    [localPlan, sessionId, onPlanUpdated]
  );

  if (!localPlan) {
    return (
      <div className={cn("rounded-lg bg-slate-800/30 border border-slate-700/50 p-6", className)}>
        <div className="flex flex-col items-center gap-3 text-slate-500">
          <Target size={32} className="opacity-30" />
          <span className="font-mono text-sm">No plan generated yet</span>
          <div className="flex gap-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="w-2 h-2 rounded-full bg-slate-600 animate-pulse"
                style={{ animationDelay: `${i * 150}ms` }}
              />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const completedCount = localPlan.tasks.filter((t) => t.status === "completed").length;
  const totalCount = localPlan.tasks.length;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div
      className={cn(
        "rounded-lg bg-slate-800/30 border border-slate-700/50 overflow-hidden",
        className
      )}
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-700/50 bg-slate-900/50">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-cyan-500/10 border border-cyan-500/30">
              <Target size={16} className="text-cyan-400" />
            </div>
            <div>
              <h3 className="font-mono text-sm font-semibold text-slate-200 uppercase tracking-wide">
                Research Plan
              </h3>
              <p className="text-slate-400 text-xs mt-0.5 max-w-md truncate">
                {localPlan.main_goal}
              </p>
            </div>
          </div>

          {/* Progress indicator */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-slate-500">
              {completedCount}/{totalCount}
            </span>
            <div className="w-20 h-2 rounded-full bg-slate-700 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* Scope info */}
        {localPlan.scope && (
          <div className="mt-3 flex items-center gap-4 text-[10px] font-mono text-slate-500">
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
              {localPlan.scope.scope.toUpperCase()}
            </span>
            <span>{localPlan.scope.target_pages} pages</span>
            <span>{localPlan.scope.target_word_count.toLocaleString()} words</span>
          </div>
        )}
      </div>

      {/* Task list */}
      <div className="p-4 space-y-3">
        {localPlan.tasks.map((task, index) => (
          <EditableTask
            key={task.id}
            task={task}
            index={index}
            totalTasks={localPlan.tasks.length}
            sessionId={sessionId}
            isEditable={isEditable && task.status === "pending"}
            onTaskUpdated={handleTaskUpdated}
            onTaskRemoved={handleTaskRemoved}
            onMoveUp={() => handleMoveTask(index, index - 1)}
            onMoveDown={() => handleMoveTask(index, index + 1)}
          />
        ))}

        {/* Add task button */}
        {isEditable && <AddTaskForm sessionId={sessionId} onTaskAdded={handleTaskAdded} />}
      </div>
    </div>
  );
}
