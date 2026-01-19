/**
 * ProgressTimeline - Visual progress bar with segmented phase indicators
 * Features glowing effects and animated progress
 */

import { cn } from "../../lib/utils";
import type { ExecutionPhase } from "../../api/status";

interface ProgressTimelineProps {
  progress: number; // 0-1
  phases: ExecutionPhase[];
  className?: string;
}

const PHASE_COLORS: Record<string, string> = {
  initializing: "from-cyan-500 to-cyan-400",
  planning: "from-violet-500 to-violet-400",
  researching: "from-emerald-500 to-emerald-400",
  reviewing: "from-amber-500 to-amber-400",
  coding: "from-orange-500 to-orange-400",
  editing: "from-sky-500 to-sky-400",
  finalizing: "from-lime-500 to-lime-400",
};

const PHASE_GLOW: Record<string, string> = {
  initializing: "shadow-cyan-500/50",
  planning: "shadow-violet-500/50",
  researching: "shadow-emerald-500/50",
  reviewing: "shadow-amber-500/50",
  coding: "shadow-orange-500/50",
  editing: "shadow-sky-500/50",
  finalizing: "shadow-lime-500/50",
};

export function ProgressTimeline({ progress, phases, className }: ProgressTimelineProps) {
  const percentage = Math.round(progress * 100);
  const currentPhase = phases.find((p) => p.is_current);
  const currentColor = currentPhase ? PHASE_COLORS[currentPhase.key] : "from-cyan-500 to-cyan-400";
  const currentGlow = currentPhase ? PHASE_GLOW[currentPhase.key] : "shadow-cyan-500/50";

  return (
    <div className={cn("space-y-3", className)}>
      {/* Main progress bar */}
      <div className="relative">
        {/* Background track with scan lines */}
        <div className="h-3 rounded-full bg-slate-800/80 border border-slate-700/50 overflow-hidden">
          {/* Scan line effect */}
          <div className="absolute inset-0 opacity-10">
            {Array.from({ length: 20 }).map((_, i) => (
              <div
                key={i}
                className="absolute h-full w-px bg-slate-400"
                style={{ left: `${(i + 1) * 5}%` }}
              />
            ))}
          </div>

          {/* Progress fill */}
          <div
            className={cn(
              "h-full rounded-full bg-gradient-to-r transition-all duration-500 ease-out",
              currentColor,
              "shadow-lg",
              currentGlow
            )}
            style={{ width: `${percentage}%` }}
          >
            {/* Animated shine effect */}
            <div className="h-full w-full relative overflow-hidden">
              <div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"
                style={{
                  transform: "skewX(-20deg)",
                  animation: "shimmer 2s infinite",
                }}
              />
            </div>
          </div>
        </div>

        {/* Percentage indicator */}
        <div
          className="absolute top-1/2 -translate-y-1/2 transition-all duration-500 pointer-events-none"
          style={{ left: `${Math.max(percentage, 3)}%` }}
        >
          <div className="relative -ml-4">
            <div
              className={cn(
                "text-[10px] font-mono font-bold px-1 rounded bg-slate-900/90 border",
                "border-slate-600 text-slate-300"
              )}
            >
              {percentage}%
            </div>
          </div>
        </div>
      </div>

      {/* Phase segments */}
      <div className="flex gap-0.5">
        {phases.map((phase) => {
          const phaseProgress = phase.progress * 100;
          const bgColor = PHASE_COLORS[phase.key] || "from-slate-500 to-slate-400";

          return (
            <div
              key={phase.key}
              className="flex-1 group relative"
              style={{ flex: phase.weight }}
            >
              {/* Phase segment background */}
              <div
                className={cn(
                  "h-1.5 rounded-sm overflow-hidden transition-all duration-300",
                  phase.is_completed
                    ? "bg-slate-600"
                    : phase.is_current
                    ? "bg-slate-700"
                    : "bg-slate-800/50"
                )}
              >
                {/* Phase progress fill */}
                <div
                  className={cn(
                    "h-full bg-gradient-to-r transition-all duration-500",
                    bgColor,
                    phase.is_current && "animate-pulse"
                  )}
                  style={{ width: `${phaseProgress}%` }}
                />
              </div>

              {/* Phase label tooltip */}
              <div
                className={cn(
                  "absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100",
                  "transition-opacity duration-200 pointer-events-none z-10"
                )}
              >
                <div className="bg-slate-800 border border-slate-600 rounded px-2 py-0.5 text-[10px] font-mono whitespace-nowrap">
                  {phase.name}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function MiniProgress({
  progress,
  phase,
  className,
}: {
  progress: number;
  phase?: string;
  className?: string;
}) {
  const percentage = Math.round(progress * 100);
  const color = phase ? PHASE_COLORS[phase] : "from-cyan-500 to-cyan-400";

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex-1 h-1 rounded-full bg-slate-800 overflow-hidden">
        <div
          className={cn("h-full bg-gradient-to-r transition-all duration-300", color)}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-[10px] font-mono text-slate-500 w-8">{percentage}%</span>
    </div>
  );
}
