/**
 * AgentIndicator - Shows active agent with heartbeat pulse animation
 * Mission Control aesthetic with radar-like scanning effect
 */

import { cn } from "../../lib/utils";
import { MiniProgress } from "./ProgressTimeline";

interface AgentIndicatorProps {
  agentName: string | null;
  tools: string[];
  progress?: number;
  className?: string;
}

const AGENT_CONFIG: Record<
  string,
  { label: string; icon: string; color: string; description: string }
> = {
  orchestrator: {
    label: "Orchestrator",
    icon: "⬢",
    color: "violet",
    description: "Planning research strategy",
  },
  researcher: {
    label: "Researcher",
    icon: "◉",
    color: "emerald",
    description: "Gathering information",
  },
  reviewer: {
    label: "Reviewer",
    icon: "◎",
    color: "amber",
    description: "Analyzing findings",
  },
  coder: {
    label: "Coder",
    icon: "⬡",
    color: "orange",
    description: "Processing data",
  },
  editor: {
    label: "Editor",
    icon: "◆",
    color: "sky",
    description: "Composing report",
  },
  error_handler: {
    label: "Recovery",
    icon: "⟳",
    color: "red",
    description: "Handling errors",
  },
};

const AGENT_COLORS: Record<string, { bg: string; text: string; border: string; glow: string }> = {
  violet: {
    bg: "bg-violet-500/10",
    text: "text-violet-400",
    border: "border-violet-500/30",
    glow: "shadow-violet-500/20",
  },
  emerald: {
    bg: "bg-emerald-500/10",
    text: "text-emerald-400",
    border: "border-emerald-500/30",
    glow: "shadow-emerald-500/20",
  },
  amber: {
    bg: "bg-amber-500/10",
    text: "text-amber-400",
    border: "border-amber-500/30",
    glow: "shadow-amber-500/20",
  },
  orange: {
    bg: "bg-orange-500/10",
    text: "text-orange-400",
    border: "border-orange-500/30",
    glow: "shadow-orange-500/20",
  },
  sky: {
    bg: "bg-sky-500/10",
    text: "text-sky-400",
    border: "border-sky-500/30",
    glow: "shadow-sky-500/20",
  },
  red: {
    bg: "bg-red-500/10",
    text: "text-red-400",
    border: "border-red-500/30",
    glow: "shadow-red-500/20",
  },
};

export function AgentIndicator({ agentName, tools, progress, className }: AgentIndicatorProps) {
  if (!agentName) {
    return (
      <div className={cn("p-4 rounded-lg bg-slate-800/30 border border-slate-700/50", className)}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center">
            <span className="text-slate-600 text-lg">○</span>
          </div>
          <div>
            <div className="text-sm font-mono text-slate-500">STANDBY</div>
            <div className="text-xs text-slate-600">Awaiting instructions</div>
          </div>
        </div>
      </div>
    );
  }

  const config = AGENT_CONFIG[agentName] || {
    label: agentName,
    icon: "●",
    color: "emerald",
    description: "Processing",
  };
  const colors = AGENT_COLORS[config.color] || AGENT_COLORS.emerald;

  return (
    <div
      className={cn(
        "relative p-4 rounded-lg border overflow-hidden transition-all duration-500",
        colors.bg,
        colors.border,
        "shadow-lg",
        colors.glow,
        className
      )}
    >
      {/* Radar sweep animation background */}
      <div className="absolute inset-0 overflow-hidden">
        <div
          className={cn(
            "absolute top-1/2 left-1/2 w-32 h-32 -translate-x-1/2 -translate-y-1/2",
            "rounded-full opacity-20",
            "animate-ping"
          )}
          style={{
            background: `radial-gradient(circle, currentColor 0%, transparent 70%)`,
            animationDuration: "2s",
          }}
        />
      </div>

      <div className="relative z-10">
        <div className="flex items-start gap-3">
          {/* Agent icon with pulse ring */}
          <div className="relative">
            <div
              className={cn(
                "w-12 h-12 rounded-lg flex items-center justify-center",
                "border-2 transition-all",
                colors.border,
                colors.bg
              )}
            >
              <span className={cn("text-2xl", colors.text)}>{config.icon}</span>
            </div>
            {/* Heartbeat pulse */}
            <div
              className={cn(
                "absolute inset-0 rounded-lg border-2 animate-ping",
                colors.border
              )}
              style={{ animationDuration: "1.5s" }}
            />
          </div>

          <div className="flex-1 min-w-0">
            {/* Agent name and status */}
            <div className="flex items-center gap-2">
              <span className={cn("font-mono font-semibold text-sm", colors.text)}>
                {config.label.toUpperCase()}
              </span>
              <span className="flex items-center gap-1">
                <span className={cn("w-1.5 h-1.5 rounded-full animate-pulse", colors.text.replace("text-", "bg-"))} />
                <span className="text-[10px] font-mono text-slate-500 uppercase">Active</span>
              </span>
            </div>

            {/* Description */}
            <div className="text-xs text-slate-400 mt-0.5">{config.description}</div>

            {/* Progress bar */}
            {typeof progress === "number" && (
              <div className="mt-2">
                <MiniProgress progress={progress} />
              </div>
            )}

            {/* Active tools */}
            {tools.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {tools.map((tool) => (
                  <span
                    key={tool}
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800/80 border border-slate-700 text-slate-400"
                  >
                    <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                    {tool}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function AgentBadge({ agentName }: { agentName: string }) {
  const config = AGENT_CONFIG[agentName] || { label: agentName, icon: "●", color: "emerald" };
  const colors = AGENT_COLORS[config.color] || AGENT_COLORS.emerald;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-xs",
        colors.bg,
        colors.text,
        "border",
        colors.border
      )}
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}
