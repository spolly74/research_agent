/**
 * ExportMenu - Dropdown menu for exporting reports in different formats
 */

import { useState, useRef, useEffect } from "react";
import { cn } from "../../lib/utils";
import { exportReport } from "../../api/reports";
import {
  Download,
  FileText,
  FileCode,
  FileType,
  ChevronDown,
  Check,
  Loader2,
} from "lucide-react";

interface ExportMenuProps {
  content: string;
  filename: string;
  className?: string;
}

interface ExportFormat {
  id: "md" | "html" | "txt";
  label: string;
  description: string;
  icon: React.ReactNode;
}

const EXPORT_FORMATS: ExportFormat[] = [
  {
    id: "md",
    label: "Markdown",
    description: "Raw markdown format",
    icon: <FileText size={14} />,
  },
  {
    id: "html",
    label: "HTML",
    description: "Web page format",
    icon: <FileCode size={14} />,
  },
  {
    id: "txt",
    label: "Plain Text",
    description: "Simple text format",
    icon: <FileType size={14} />,
  },
];

export function ExportMenu({ content, filename, className }: ExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [exported, setExported] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleExport = async (format: ExportFormat) => {
    setExporting(format.id);

    try {
      // Small delay for visual feedback
      await new Promise((resolve) => setTimeout(resolve, 300));

      let exportContent = content;

      // Convert markdown to HTML if needed
      if (format.id === "html") {
        // Basic markdown to HTML conversion (for simple cases)
        exportContent = content
          .replace(/^### (.*$)/gm, "<h3>$1</h3>")
          .replace(/^## (.*$)/gm, "<h2>$1</h2>")
          .replace(/^# (.*$)/gm, "<h1>$1</h1>")
          .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
          .replace(/\*(.*?)\*/g, "<em>$1</em>")
          .replace(/`(.*?)`/g, "<code>$1</code>")
          .replace(/\n/g, "<br>\n");
      }

      exportReport(exportContent, filename, format.id);
      setExported(format.id);
      setTimeout(() => setExported(null), 2000);
    } catch (error) {
      console.error("Export failed:", error);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div ref={menuRef} className={cn("relative", className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-1 px-2 py-2 rounded-lg transition-colors",
          isOpen
            ? "bg-cyan-500/20 text-cyan-400"
            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
        )}
        title="Export report"
      >
        <Download size={16} />
        <ChevronDown size={12} className={cn("transition-transform", isOpen && "rotate-180")} />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-56 bg-slate-900 border border-slate-700 rounded-lg shadow-xl shadow-slate-950/50 overflow-hidden z-50">
          <div className="px-3 py-2 border-b border-slate-800">
            <p className="text-xs font-mono text-slate-500 uppercase tracking-wider">
              Export As
            </p>
          </div>

          <div className="p-1">
            {EXPORT_FORMATS.map((format) => (
              <button
                key={format.id}
                onClick={() => handleExport(format)}
                disabled={exporting !== null}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors",
                  "hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed",
                  exported === format.id && "bg-emerald-500/10"
                )}
              >
                <div
                  className={cn(
                    "p-1.5 rounded",
                    exported === format.id
                      ? "bg-emerald-500/20 text-emerald-400"
                      : "bg-slate-800 text-slate-400"
                  )}
                >
                  {exporting === format.id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : exported === format.id ? (
                    <Check size={14} />
                  ) : (
                    format.icon
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      "text-sm font-medium",
                      exported === format.id ? "text-emerald-400" : "text-slate-200"
                    )}
                  >
                    {format.label}
                  </p>
                  <p className="text-[10px] text-slate-500">{format.description}</p>
                </div>

                {exported === format.id && (
                  <span className="text-[10px] font-mono text-emerald-400">Downloaded</span>
                )}
              </button>
            ))}
          </div>

          {/* PDF note */}
          <div className="px-3 py-2 border-t border-slate-800 bg-slate-800/30">
            <p className="text-[10px] text-slate-500">
              For PDF export, use Print → Save as PDF
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
