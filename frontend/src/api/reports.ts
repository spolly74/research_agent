/**
 * Reports API - Endpoints for report generation, formatting, and citations
 */

const API_BASE = "http://localhost:8000/api";

export interface ReportTemplate {
  name: string;
  description: string;
  sections: string[];
  best_for: string;
}

export interface ReportSection {
  type: string;
  title: string;
  order: number;
  is_required: boolean;
  word_count_target: number;
  notes?: string;
}

export interface ReportTemplateDetail {
  name: string;
  description: string;
  report_type: string;
  sections: ReportSection[];
}

export interface ReportScope {
  name: string;
  target_pages: number;
  target_word_count: number;
  min_sources: number;
  max_sources: number;
  section_depth: number;
  description: string;
}

export interface Citation {
  id: string;
  url: string;
  title?: string;
  author?: string;
  publisher?: string;
  publication_date?: string;
  accessed_date?: string;
  content_snippet?: string;
}

export interface CitationStyle {
  name: string;
  description: string;
  example: string;
}

export interface ReportOutline {
  title: string;
  report_type: string;
  sections: {
    type: string;
    title: string;
    content?: string;
    subsections?: { title: string; content?: string }[];
  }[];
  total_word_count?: number;
}

export interface ParsedReport {
  title: string;
  sections: ParsedSection[];
  citations: Citation[];
  metadata: {
    report_type?: string;
    scope?: string;
    word_count?: number;
  };
}

export interface ParsedSection {
  id: string;
  title: string;
  level: number;
  content: string;
  children?: ParsedSection[];
}

// List available templates
export async function listTemplates(): Promise<Record<string, ReportTemplate>> {
  try {
    const response = await fetch(`${API_BASE}/reports/templates`);
    if (!response.ok) return {};
    const data = await response.json();
    return data.templates || {};
  } catch (error) {
    console.error("Failed to fetch templates:", error);
    return {};
  }
}

// Get detailed template info
export async function getTemplate(templateType: string): Promise<ReportTemplateDetail | null> {
  try {
    const response = await fetch(`${API_BASE}/reports/templates/${templateType}`);
    if (!response.ok) return null;
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch template:", error);
    return null;
  }
}

// List available scopes
export async function listScopes(): Promise<Record<string, ReportScope>> {
  try {
    const response = await fetch(`${API_BASE}/reports/scopes`);
    if (!response.ok) return {};
    const data = await response.json();
    return data.scopes || {};
  } catch (error) {
    console.error("Failed to fetch scopes:", error);
    return {};
  }
}

// List citation styles
export async function listCitationStyles(): Promise<Record<string, CitationStyle>> {
  try {
    const response = await fetch(`${API_BASE}/reports/citation-styles`);
    if (!response.ok) return {};
    const data = await response.json();
    return data.styles || {};
  } catch (error) {
    console.error("Failed to fetch citation styles:", error);
    return {};
  }
}

// Get all citations
export async function getCitations(): Promise<Citation[]> {
  try {
    const response = await fetch(`${API_BASE}/reports/citations`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.citations || [];
  } catch (error) {
    console.error("Failed to fetch citations:", error);
    return [];
  }
}

// Generate bibliography
export async function generateBibliography(style: string = "apa"): Promise<string> {
  try {
    const response = await fetch(`${API_BASE}/reports/bibliography`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ style }),
    });
    if (!response.ok) return "";
    const data = await response.json();
    return data.bibliography || "";
  } catch (error) {
    console.error("Failed to generate bibliography:", error);
    return "";
  }
}

// Format report content
export async function formatReport(
  title: string,
  researchData: string[],
  options: {
    report_type?: string;
    format?: "markdown" | "html";
    include_toc?: boolean;
    scope?: string;
    target_pages?: number;
  } = {}
): Promise<{ content: string; word_count: number; sections: number } | null> {
  try {
    const response = await fetch(`${API_BASE}/reports/format`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        research_data: researchData,
        report_type: options.report_type,
        format: options.format || "markdown",
        include_toc: options.include_toc ?? true,
        scope: options.scope,
        target_pages: options.target_pages,
      }),
    });
    if (!response.ok) return null;
    const data = await response.json();
    return {
      content: data.content,
      word_count: data.word_count,
      sections: data.sections,
    };
  } catch (error) {
    console.error("Failed to format report:", error);
    return null;
  }
}

// Parse markdown content into structured sections
export function parseMarkdownReport(content: string): ParsedReport {
  const lines = content.split("\n");
  const sections: ParsedSection[] = [];
  let currentSection: ParsedSection | null = null;
  let title = "";
  let sectionIdCounter = 0;

  const generateId = () => `section-${sectionIdCounter++}`;

  for (const line of lines) {
    // Check for headings
    const h1Match = line.match(/^#\s+(.+)$/);
    const h2Match = line.match(/^##\s+(.+)$/);
    const h3Match = line.match(/^###\s+(.+)$/);

    if (h1Match) {
      // Title or main section
      if (!title) {
        title = h1Match[1];
      } else {
        if (currentSection) sections.push(currentSection);
        currentSection = {
          id: generateId(),
          title: h1Match[1],
          level: 1,
          content: "",
          children: [],
        };
      }
    } else if (h2Match) {
      if (currentSection) sections.push(currentSection);
      currentSection = {
        id: generateId(),
        title: h2Match[1],
        level: 2,
        content: "",
        children: [],
      };
    } else if (h3Match && currentSection) {
      // Add as subsection
      currentSection.children = currentSection.children || [];
      currentSection.children.push({
        id: generateId(),
        title: h3Match[1],
        level: 3,
        content: "",
      });
    } else if (currentSection) {
      // Add content
      if (currentSection.children && currentSection.children.length > 0) {
        const lastChild = currentSection.children[currentSection.children.length - 1];
        lastChild.content += line + "\n";
      } else {
        currentSection.content += line + "\n";
      }
    }
  }

  if (currentSection) sections.push(currentSection);

  // Extract citations from content (basic pattern matching)
  const citationMatches = content.match(/\[(\d+)\]/g) || [];
  const citations: Citation[] = citationMatches.map((match, i) => ({
    id: `citation-${i}`,
    url: "",
    title: `Reference ${match}`,
  }));

  return {
    title,
    sections,
    citations,
    metadata: {
      word_count: content.split(/\s+/).length,
    },
  };
}

// Export report as downloadable file
export function exportReport(
  content: string,
  filename: string,
  format: "md" | "html" | "txt"
): void {
  let mimeType = "text/plain";
  let fileContent = content;

  switch (format) {
    case "md":
      mimeType = "text/markdown";
      break;
    case "html":
      mimeType = "text/html";
      // Wrap in basic HTML structure if not already HTML
      if (!content.trim().startsWith("<!DOCTYPE") && !content.trim().startsWith("<html")) {
        fileContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${filename}</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }
    h1, h2, h3 { margin-top: 2em; }
    pre { background: #f4f4f4; padding: 1em; overflow-x: auto; }
    blockquote { border-left: 4px solid #ddd; margin: 0; padding-left: 1em; color: #666; }
  </style>
</head>
<body>
${content}
</body>
</html>`;
      }
      break;
  }

  const blob = new Blob([fileContent], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename}.${format}`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
