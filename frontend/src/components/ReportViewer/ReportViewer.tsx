/**
 * ReportViewer - Professional report viewer with TOC, export, and citation previews
 * Features a clean reading experience with navigation and export capabilities
 */

import { useState, useRef, useEffect, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "../../lib/utils";
import { parseMarkdownReport, exportReport, type ParsedSection, type Citation } from "../../api/reports";
import { TableOfContents } from "./TableOfContents";
import { CitationTooltip } from "./CitationTooltip";
import { ExportMenu } from "./ExportMenu";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  FileText,
  List,
  Download,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  Printer,
} from "lucide-react";

interface ReportViewerProps {
  content: string;
  title?: string;
  citations?: Citation[];
  className?: string;
  showToc?: boolean;
  onClose?: () => void;
}

export function ReportViewer({
  content,
  title,
  citations = [],
  className,
  showToc = true,
  onClose,
}: ReportViewerProps) {
  const [isTocOpen, setIsTocOpen] = useState(showToc);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // Parse the markdown content
  const parsedReport = useMemo(() => parseMarkdownReport(content), [content]);
  const reportTitle = title || parsedReport.title || "Research Report";
  const allCitations = citations.length > 0 ? citations : parsedReport.citations;

  // Track scroll position to highlight TOC
  useEffect(() => {
    const handleScroll = () => {
      if (!contentRef.current) return;

      const sections = contentRef.current.querySelectorAll("[data-section-id]");
      let currentActive: string | null = null;

      sections.forEach((section) => {
        const rect = section.getBoundingClientRect();
        if (rect.top <= 150) {
          currentActive = section.getAttribute("data-section-id");
        }
      });

      setActiveSection(currentActive);
    };

    const container = contentRef.current;
    if (container) {
      container.addEventListener("scroll", handleScroll);
      return () => container.removeEventListener("scroll", handleScroll);
    }
  }, []);

  // Scroll to section
  const scrollToSection = (sectionId: string) => {
    const element = contentRef.current?.querySelector(`[data-section-id="${sectionId}"]`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  // Copy content to clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  // Print report
  const handlePrint = () => {
    window.print();
  };

  // Toggle fullscreen
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  // Word count
  const wordCount = useMemo(() => content.split(/\s+/).filter(Boolean).length, [content]);

  return (
    <div
      className={cn(
        "flex flex-col bg-slate-950 rounded-xl border border-slate-800 overflow-hidden",
        isFullscreen && "fixed inset-0 z-50 rounded-none",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/50">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
            <BookOpen size={16} className="text-emerald-400" />
          </div>
          <div>
            <h2 className="font-semibold text-slate-200 text-sm truncate max-w-[300px]">
              {reportTitle}
            </h2>
            <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
              <span>{wordCount.toLocaleString()} words</span>
              <span>{parsedReport.sections.length} sections</span>
              {allCitations.length > 0 && <span>{allCitations.length} citations</span>}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {/* TOC toggle */}
          <button
            onClick={() => setIsTocOpen(!isTocOpen)}
            className={cn(
              "p-2 rounded-lg transition-colors",
              isTocOpen
                ? "bg-cyan-500/20 text-cyan-400"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            )}
            title="Table of Contents"
          >
            <List size={16} />
          </button>

          {/* Copy */}
          <button
            onClick={handleCopy}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title="Copy to clipboard"
          >
            {copied ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
          </button>

          {/* Print */}
          <button
            onClick={handlePrint}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors print:hidden"
            title="Print report"
          >
            <Printer size={16} />
          </button>

          {/* Export */}
          <ExportMenu
            content={content}
            filename={reportTitle.toLowerCase().replace(/\s+/g, "-")}
          />

          {/* Fullscreen */}
          <button
            onClick={toggleFullscreen}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>

          {/* Close */}
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors"
              title="Close"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Table of Contents sidebar */}
        {isTocOpen && (
          <div className="w-64 border-r border-slate-800 flex-shrink-0 overflow-y-auto bg-slate-900/30 print:hidden">
            <TableOfContents
              sections={parsedReport.sections}
              activeSection={activeSection}
              onSectionClick={scrollToSection}
            />
          </div>
        )}

        {/* Main content */}
        <div
          ref={contentRef}
          className="flex-1 overflow-y-auto p-6 md:p-10"
        >
          <article className="max-w-3xl mx-auto prose prose-invert prose-slate prose-sm md:prose-base">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Custom heading renderers with section IDs
                h1: ({ children, ...props }) => {
                  const id = `section-${String(children).toLowerCase().replace(/\s+/g, "-")}`;
                  return (
                    <h1
                      {...props}
                      data-section-id={id}
                      className="text-2xl md:text-3xl font-bold text-slate-100 border-b border-slate-800 pb-3 mb-6"
                    >
                      {children}
                    </h1>
                  );
                },
                h2: ({ children, ...props }) => {
                  const id = `section-${String(children).toLowerCase().replace(/\s+/g, "-")}`;
                  return (
                    <h2
                      {...props}
                      data-section-id={id}
                      className="text-xl md:text-2xl font-semibold text-slate-200 mt-10 mb-4 scroll-mt-4"
                    >
                      {children}
                    </h2>
                  );
                },
                h3: ({ children, ...props }) => {
                  const id = `section-${String(children).toLowerCase().replace(/\s+/g, "-")}`;
                  return (
                    <h3
                      {...props}
                      data-section-id={id}
                      className="text-lg md:text-xl font-medium text-slate-300 mt-8 mb-3 scroll-mt-4"
                    >
                      {children}
                    </h3>
                  );
                },
                // Custom paragraph with citation detection
                p: ({ children, ...props }) => (
                  <p {...props} className="text-slate-300 leading-relaxed mb-4">
                    <CitationTooltip citations={allCitations}>{children}</CitationTooltip>
                  </p>
                ),
                // Custom code blocks
                pre: ({ children, ...props }) => (
                  <pre
                    {...props}
                    className="bg-slate-900 border border-slate-800 rounded-lg p-4 overflow-x-auto my-4"
                  >
                    {children}
                  </pre>
                ),
                code: ({ children, className, ...props }) => {
                  const isInline = !className;
                  return isInline ? (
                    <code
                      {...props}
                      className="bg-slate-800 text-cyan-400 px-1.5 py-0.5 rounded text-sm font-mono"
                    >
                      {children}
                    </code>
                  ) : (
                    <code {...props} className="text-slate-300 text-sm font-mono">
                      {children}
                    </code>
                  );
                },
                // Custom links
                a: ({ href, children, ...props }) => (
                  <a
                    {...props}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2 transition-colors"
                  >
                    {children}
                  </a>
                ),
                // Custom blockquotes
                blockquote: ({ children, ...props }) => (
                  <blockquote
                    {...props}
                    className="border-l-4 border-cyan-500/50 pl-4 my-4 text-slate-400 italic"
                  >
                    {children}
                  </blockquote>
                ),
                // Custom lists
                ul: ({ children, ...props }) => (
                  <ul {...props} className="list-disc list-inside space-y-1 text-slate-300 mb-4">
                    {children}
                  </ul>
                ),
                ol: ({ children, ...props }) => (
                  <ol {...props} className="list-decimal list-inside space-y-1 text-slate-300 mb-4">
                    {children}
                  </ol>
                ),
                // Custom table
                table: ({ children, ...props }) => (
                  <div className="overflow-x-auto my-4">
                    <table
                      {...props}
                      className="min-w-full border border-slate-700 rounded-lg overflow-hidden"
                    >
                      {children}
                    </table>
                  </div>
                ),
                th: ({ children, ...props }) => (
                  <th
                    {...props}
                    className="bg-slate-800 px-4 py-2 text-left text-sm font-medium text-slate-200 border-b border-slate-700"
                  >
                    {children}
                  </th>
                ),
                td: ({ children, ...props }) => (
                  <td
                    {...props}
                    className="px-4 py-2 text-sm text-slate-300 border-b border-slate-800"
                  >
                    {children}
                  </td>
                ),
                // Horizontal rule
                hr: (props) => <hr {...props} className="border-slate-700 my-8" />,
              }}
            >
              {content}
            </ReactMarkdown>
          </article>
        </div>
      </div>

      {/* Print styles */}
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          .prose, .prose * {
            visibility: visible;
          }
          .prose {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            color: black !important;
          }
          .prose h1, .prose h2, .prose h3 {
            color: black !important;
          }
          .prose p, .prose li {
            color: #333 !important;
          }
        }
      `}</style>
    </div>
  );
}
