/**
 * PhaseIndicator - Shows current execution phase with glowing badge
 * Mission Control aesthetic with neon glow effects
 */

import { cn } from "../../lib/utils";

interface PhaseIndicatorProps {
  phase: string;
  isActive?: boolean;
  className?: string;
}

const PHASE_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  initializing: {
    label: "INIT",
    color: "cyan",
    icon: "◈",
  },
  planning: {
    label: "PLAN",
    color: "violet",
    icon: "◇",
  },
  researching: {
    label: "RSRCH",
    color: "emerald",
    icon: "◉",
  },
  reviewing: {
    label: "REVW",
    color: "amber",
    icon: "◎",
  },
  coding: {
    label: "CODE",
    color: "orange",
    icon: "⬡",
  },
  editing: {
    label: "EDIT",
    color: "sky",
    icon: "◆",
  },
  finalizing: {
    label: "FINAL",
    color: "lime",
    icon: "✦",
  },
  completed: {
    label: "DONE",
    color: "green",
    icon: "✓",
  },
  error: {
    label: "ERR",
    color: "red",
    icon: "✕",
  },
};

const colorClasses: Record<string, string> = {
  cyan: "bg-cyan-500/20 text-cyan-400 border-cyan-500/50 shadow-cyan-500/25",
  violet: "bg-violet-500/20 text-violet-400 border-violet-500/50 shadow-violet-500/25",
  emerald: "bg-emerald-500/20 text-emerald-400 border-emerald-500/50 shadow-emerald-500/25",
  amber: "bg-amber-500/20 text-amber-400 border-amber-500/50 shadow-amber-500/25",
  orange: "bg-orange-500/20 text-orange-400 border-orange-500/50 shadow-orange-500/25",
  sky: "bg-sky-500/20 text-sky-400 border-sky-500/50 shadow-sky-500/25",
  lime: "bg-lime-500/20 text-lime-400 border-lime-500/50 shadow-lime-500/25",
  green: "bg-green-500/20 text-green-400 border-green-500/50 shadow-green-500/25",
  red: "bg-red-500/20 text-red-400 border-red-500/50 shadow-red-500/25",
};

export function PhaseIndicator({ phase, isActive = false, className }: PhaseIndicatorProps) {
  const config = PHASE_CONFIG[phase] || { label: phase.toUpperCase(), color: "cyan", icon: "●" };
  const colors = colorClasses[config.color] || colorClasses.cyan;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded border font-mono text-xs tracking-wider",
        "transition-all duration-300",
        colors,
        isActive && "shadow-lg animate-pulse",
        className
      )}
    >
      <span className={cn("text-sm", isActive && "animate-spin-slow")}>{config.icon}</span>
      <span className="font-semibold">{config.label}</span>
    </div>
  );
}

export function PhaseRow({
  phases,
  currentPhase,
}: {
  phases: string[];
  currentPhase: string;
}) {
  const currentIndex = phases.indexOf(currentPhase);

  return (
    <div className="flex items-center gap-1">
      {phases.map((phase, index) => {
        const isCompleted = index < currentIndex;
        const isCurrent = phase === currentPhase;
        const isPending = index > currentIndex;
        const config = PHASE_CONFIG[phase] || { label: phase, color: "cyan", icon: "●" };
        const colors = colorClasses[config.color] || colorClasses.cyan;

        return (
          <div key={phase} className="flex items-center">
            <div
              className={cn(
                "w-8 h-8 rounded-sm flex items-center justify-center font-mono text-xs border transition-all duration-500",
                isCurrent && cn(colors, "shadow-lg"),
                isCompleted && "bg-slate-700/50 text-slate-400 border-slate-600",
                isPending && "bg-slate-800/30 text-slate-600 border-slate-700/50"
              )}
              title={config.label}
            >
              {isCompleted ? "✓" : config.icon}
            </div>
            {index < phases.length - 1 && (
              <div
                className={cn(
                  "w-4 h-0.5 transition-all duration-500",
                  index < currentIndex ? "bg-slate-500" : "bg-slate-700/50"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
