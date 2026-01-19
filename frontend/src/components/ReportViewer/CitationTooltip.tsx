/**
 * CitationTooltip - Wraps text and shows citation previews on hover
 * Detects [1], [2], etc. citation markers and shows tooltip with details
 */

import { useState, useRef, useEffect, type ReactNode } from "react";
import { cn } from "../../lib/utils";
import { type Citation } from "../../api/reports";
import { ExternalLink, BookMarked, User, Calendar } from "lucide-react";

interface CitationTooltipProps {
  children: ReactNode;
  citations: Citation[];
  className?: string;
}

interface TooltipPosition {
  x: number;
  y: number;
  citation: Citation | null;
}

export function CitationTooltip({ children, citations, className }: CitationTooltipProps) {
  const [tooltip, setTooltip] = useState<TooltipPosition | null>(null);
  const containerRef = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Find citation by number
  const findCitation = (num: number): Citation | null => {
    return citations[num - 1] || null;
  };

  // Handle mouse events
  const handleMouseOver = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.dataset.citationNum) {
      const num = parseInt(target.dataset.citationNum, 10);
      const citation = findCitation(num);
      if (citation) {
        const rect = target.getBoundingClientRect();
        setTooltip({
          x: rect.left + rect.width / 2,
          y: rect.bottom + 8,
          citation,
        });
      }
    }
  };

  const handleMouseOut = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.dataset.citationNum) {
      setTooltip(null);
    }
  };

  // Process children to wrap citation markers
  const processChildren = (child: ReactNode): ReactNode => {
    if (typeof child === "string") {
      // Find citation markers like [1], [2], etc.
      const parts = child.split(/(\[\d+\])/g);
      return parts.map((part, i) => {
        const match = part.match(/^\[(\d+)\]$/);
        if (match) {
          const num = parseInt(match[1], 10);
          const hasCitation = findCitation(num) !== null;
          return (
            <span
              key={i}
              data-citation-num={num}
              className={cn(
                "cursor-help transition-colors",
                hasCitation
                  ? "text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded px-0.5"
                  : "text-slate-500"
              )}
            >
              {part}
            </span>
          );
        }
        return part;
      });
    }

    if (Array.isArray(child)) {
      return child.map(processChildren);
    }

    return child;
  };

  return (
    <span
      ref={containerRef}
      className={cn("relative", className)}
      onMouseOver={handleMouseOver}
      onMouseOut={handleMouseOut}
    >
      {processChildren(children)}

      {/* Tooltip */}
      {tooltip && tooltip.citation && (
        <div
          ref={tooltipRef}
          className="fixed z-50 pointer-events-none"
          style={{
            left: Math.min(tooltip.x, window.innerWidth - 320),
            top: tooltip.y,
            transform: "translateX(-50%)",
          }}
        >
          <div className="w-72 bg-slate-900 border border-slate-700 rounded-lg shadow-xl shadow-slate-950/50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Header */}
            <div className="px-3 py-2 bg-slate-800/50 border-b border-slate-700">
              <div className="flex items-center gap-2">
                <BookMarked size={12} className="text-cyan-400" />
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
                  Citation Preview
                </span>
              </div>
            </div>

            {/* Content */}
            <div className="p-3 space-y-2">
              {/* Title */}
              {tooltip.citation.title && (
                <p className="text-sm font-medium text-slate-200 line-clamp-2">
                  {tooltip.citation.title}
                </p>
              )}

              {/* Author */}
              {tooltip.citation.author && (
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <User size={10} />
                  <span>{tooltip.citation.author}</span>
                </div>
              )}

              {/* Date */}
              {(tooltip.citation.publication_date || tooltip.citation.accessed_date) && (
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <Calendar size={10} />
                  <span>
                    {tooltip.citation.publication_date || `Accessed ${tooltip.citation.accessed_date}`}
                  </span>
                </div>
              )}

              {/* URL */}
              {tooltip.citation.url && (
                <div className="flex items-center gap-2 text-xs">
                  <ExternalLink size={10} className="text-slate-500 flex-shrink-0" />
                  <span className="text-cyan-400 truncate">{tooltip.citation.url}</span>
                </div>
              )}

              {/* Content snippet */}
              {tooltip.citation.content_snippet && (
                <p className="text-xs text-slate-500 line-clamp-3 pt-2 border-t border-slate-800 italic">
                  "{tooltip.citation.content_snippet}"
                </p>
              )}
            </div>

            {/* Arrow */}
            <div
              className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-900 border-l border-t border-slate-700 rotate-45"
            />
          </div>
        </div>
      )}
    </span>
  );
}

/**
 * CitationList - Standalone list of citations/references
 */
interface CitationListProps {
  citations: Citation[];
  style?: "apa" | "mla" | "chicago" | "ieee";
  className?: string;
}

export function CitationList({ citations, style = "apa", className }: CitationListProps) {
  if (citations.length === 0) {
    return null;
  }

  const formatCitation = (citation: Citation, index: number): string => {
    const num = index + 1;
    const author = citation.author || "Unknown";
    const title = citation.title || "Untitled";
    const url = citation.url || "";

    switch (style) {
      case "apa":
        return `${author}. (${citation.publication_date || "n.d."}). ${title}. Retrieved from ${url}`;
      case "mla":
        return `${author}. "${title}." Web. ${citation.accessed_date || "n.d."}.`;
      case "chicago":
        return `${author}. "${title}." Accessed ${citation.accessed_date || "n.d."}. ${url}.`;
      case "ieee":
        return `[${num}] ${author}, "${title}," ${citation.publication_date || "n.d."}. [Online]. Available: ${url}`;
      default:
        return `[${num}] ${title}. ${url}`;
    }
  };

  return (
    <div className={cn("space-y-3", className)}>
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
        References
      </h3>
      <ol className="space-y-2 list-none">
        {citations.map((citation, index) => (
          <li key={citation.id || index} className="text-sm text-slate-400 pl-6 relative">
            <span className="absolute left-0 text-slate-500">[{index + 1}]</span>
            {formatCitation(citation, index)}
          </li>
        ))}
      </ol>
    </div>
  );
}
