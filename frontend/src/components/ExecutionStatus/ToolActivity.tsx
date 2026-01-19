/**
 * ToolActivity - Terminal-style activity log with typing animation
 * Shows real-time tool invocations and events
 */

import { useRef, useEffect } from "react";
import { cn } from "../../lib/utils";
import type { ActivityLogEntry } from "../../hooks/useExecutionStatus";
import { Terminal, Wifi, WifiOff } from "lucide-react";

interface ToolActivityProps {
  entries: ActivityLogEntry[];
  isConnected: boolean;
  className?: string;
  maxHeight?: string;
}

const TYPE_CONFIG: Record<
  string,
  { prefix: string; color: string; bgColor: string }
> = {
  phase: {
    prefix: "PHASE",
    color: "text-violet-400",
    bgColor: "bg-violet-500/10",
  },
  agent: {
    prefix: "AGENT",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/10",
  },
  tool: {
    prefix: "TOOL",
    color: "text-cyan-400",
    bgColor: "bg-cyan-500/10",
  },
  message: {
    prefix: "INFO",
    color: "text-slate-400",
    bgColor: "bg-slate-500/10",
  },
  error: {
    prefix: "ERROR",
    color: "text-red-400",
    bgColor: "bg-red-500/10",
  },
  complete: {
    prefix: "DONE",
    color: "text-lime-400",
    bgColor: "bg-lime-500/10",
  },
};

function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function LogEntry({ entry, isLatest }: { entry: ActivityLogEntry; isLatest: boolean }) {
  const config = TYPE_CONFIG[entry.type] || TYPE_CONFIG.message;

  return (
    <div
      className={cn(
        "flex items-start gap-2 py-1 px-2 rounded text-xs font-mono",
        "transition-all duration-300",
        isLatest && "animate-fade-in",
        config.bgColor
      )}
    >
      {/* Timestamp */}
      <span className="text-slate-600 flex-shrink-0 tabular-nums">
        {formatTimestamp(entry.timestamp)}
      </span>

      {/* Type badge */}
      <span
        className={cn(
          "flex-shrink-0 px-1 py-0.5 rounded text-[10px] font-semibold",
          config.color,
          "bg-slate-800/50 border border-slate-700/50"
        )}
      >
        {config.prefix}
      </span>

      {/* Content */}
      <span className={cn("flex-1", config.color)}>{entry.content}</span>

      {/* Blinking cursor for latest entry */}
      {isLatest && (
        <span className="w-1.5 h-3.5 bg-current animate-blink opacity-70" />
      )}
    </div>
  );
}

export function ToolActivity({
  entries,
  isConnected,
  className,
  maxHeight = "200px",
}: ToolActivityProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest entry
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [entries]);

  return (
    <div
      className={cn(
        "rounded-lg bg-slate-900/80 border border-slate-700/50 overflow-hidden",
        className
      )}
    >
      {/* Terminal header */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-800/80 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <Terminal size={12} className="text-slate-500" />
          <span className="font-mono text-xs text-slate-400">ACTIVITY LOG</span>
        </div>

        {/* Connection status */}
        <div className="flex items-center gap-1.5">
          {isConnected ? (
            <>
              <Wifi size={10} className="text-emerald-500" />
              <span className="text-[10px] font-mono text-emerald-500">LIVE</span>
            </>
          ) : (
            <>
              <WifiOff size={10} className="text-amber-500" />
              <span className="text-[10px] font-mono text-amber-500">POLLING</span>
            </>
          )}
        </div>
      </div>

      {/* Log content */}
      <div
        ref={scrollRef}
        className="overflow-y-auto p-1 space-y-0.5"
        style={{ maxHeight }}
      >
        {entries.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-slate-600">
            <span className="font-mono text-xs">Waiting for activity...</span>
            <span className="ml-1 w-1.5 h-3 bg-slate-600 animate-blink" />
          </div>
        ) : (
          entries.map((entry, index) => (
            <LogEntry key={entry.id} entry={entry} isLatest={index === 0} />
          ))
        )}
      </div>

      {/* Scan line effect overlay */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-slate-900/5 to-transparent animate-scan-line" />
    </div>
  );
}

export function CompactActivity({
  entries,
  limit = 3,
}: {
  entries: ActivityLogEntry[];
  limit?: number;
}) {
  const recentEntries = entries.slice(0, limit);

  return (
    <div className="space-y-1">
      {recentEntries.map((entry, index) => {
        const config = TYPE_CONFIG[entry.type] || TYPE_CONFIG.message;
        return (
          <div
            key={entry.id}
            className={cn(
              "text-xs font-mono px-2 py-1 rounded",
              "transition-opacity duration-500",
              index === 0 ? "opacity-100" : "opacity-50"
            )}
          >
            <span className={config.color}>{entry.content}</span>
          </div>
        );
      })}
    </div>
  );
}
