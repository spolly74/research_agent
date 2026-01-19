/**
 * TableOfContents - Navigable section list for reports
 * Highlights current section and allows quick navigation
 */

import { cn } from "../../lib/utils";
import { type ParsedSection } from "../../api/reports";
import { ChevronRight, Hash } from "lucide-react";

interface TableOfContentsProps {
  sections: ParsedSection[];
  activeSection: string | null;
  onSectionClick: (sectionId: string) => void;
  className?: string;
}

function TocItem({
  section,
  activeSection,
  onSectionClick,
  depth = 0,
}: {
  section: ParsedSection;
  activeSection: string | null;
  onSectionClick: (sectionId: string) => void;
  depth?: number;
}) {
  const isActive = activeSection === section.id;
  const generatedId = `section-${section.title.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <div>
      <button
        onClick={() => onSectionClick(generatedId)}
        className={cn(
          "w-full text-left px-3 py-2 rounded-lg text-sm transition-all duration-200 flex items-center gap-2 group",
          depth === 0 && "font-medium",
          depth === 1 && "pl-6 text-xs",
          depth === 2 && "pl-9 text-xs",
          isActive
            ? "bg-cyan-500/10 text-cyan-400 border-l-2 border-cyan-500"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
        )}
      >
        <Hash
          size={depth === 0 ? 12 : 10}
          className={cn(
            "flex-shrink-0 opacity-50 group-hover:opacity-100 transition-opacity",
            isActive && "opacity-100"
          )}
        />
        <span className="truncate">{section.title}</span>
        {isActive && (
          <ChevronRight size={12} className="ml-auto flex-shrink-0 text-cyan-400" />
        )}
      </button>

      {/* Render children */}
      {section.children && section.children.length > 0 && (
        <div className="mt-1 space-y-0.5">
          {section.children.map((child) => (
            <TocItem
              key={child.id}
              section={child}
              activeSection={activeSection}
              onSectionClick={onSectionClick}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function TableOfContents({
  sections,
  activeSection,
  onSectionClick,
  className,
}: TableOfContentsProps) {
  if (sections.length === 0) {
    return (
      <div className={cn("p-4", className)}>
        <div className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">
          Contents
        </div>
        <p className="text-xs text-slate-600">No sections found</p>
      </div>
    );
  }

  return (
    <nav className={cn("p-3", className)}>
      <div className="flex items-center gap-2 px-3 py-2 text-xs font-mono text-slate-500 uppercase tracking-wider">
        <span>Contents</span>
        <span className="text-slate-600">({sections.length})</span>
      </div>

      <div className="mt-2 space-y-0.5">
        {sections.map((section) => (
          <TocItem
            key={section.id}
            section={section}
            activeSection={activeSection}
            onSectionClick={onSectionClick}
          />
        ))}
      </div>

      {/* Progress indicator */}
      <div className="mt-4 px-3">
        <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-cyan-500 to-emerald-500 transition-all duration-300"
            style={{
              width: `${Math.min(
                100,
                ((sections.findIndex(
                  (s) => `section-${s.title.toLowerCase().replace(/\s+/g, "-")}` === activeSection
                ) + 1) / sections.length) * 100
              )}%`,
            }}
          />
        </div>
        <p className="text-[10px] font-mono text-slate-600 mt-1 text-center">
          Reading progress
        </p>
      </div>
    </nav>
  );
}
