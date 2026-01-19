/**
 * ToolCreateWizard - Multi-step wizard for creating custom tools
 * Guides users through defining name, description, code, and configuration
 */

import { useState } from "react";
import { cn } from "../../lib/utils";
import {
  createTool,
  type ToolCategory,
  type ToolCreateRequest,
  CATEGORY_INFO,
} from "../../api/tools";
import {
  Sparkles,
  ChevronRight,
  ChevronLeft,
  Check,
  Loader2,
  AlertCircle,
  Code2,
  FileText,
  Settings,
  Wand2,
  Copy,
  X,
  Info,
  Lightbulb,
} from "lucide-react";

interface ToolCreateWizardProps {
  onClose?: () => void;
  onSuccess?: (toolName: string) => void;
  className?: string;
}

type WizardStep = "basics" | "code" | "config" | "review";

const STEPS: { id: WizardStep; label: string; icon: React.ReactNode }[] = [
  { id: "basics", label: "Basics", icon: <FileText size={14} /> },
  { id: "code", label: "Code", icon: <Code2 size={14} /> },
  { id: "config", label: "Config", icon: <Settings size={14} /> },
  { id: "review", label: "Review", icon: <Check size={14} /> },
];

const AGENT_TYPES = ["researcher", "coder", "reviewer", "editor"];

const CODE_TEMPLATE = `def my_tool(input_text: str) -> str:
    """
    Description of what this tool does.

    Args:
        input_text: The input to process

    Returns:
        The processed result
    """
    # Your code here
    result = input_text.upper()
    return result`;

const CODE_EXAMPLES = [
  {
    name: "Text Processor",
    description: "Process and transform text",
    code: `def text_processor(text: str, operation: str = "upper") -> str:
    """Process text with various operations."""
    if operation == "upper":
        return text.upper()
    elif operation == "lower":
        return text.lower()
    elif operation == "reverse":
        return text[::-1]
    elif operation == "count":
        return str(len(text.split()))
    return text`,
  },
  {
    name: "JSON Formatter",
    description: "Format and validate JSON",
    code: `def json_formatter(json_str: str) -> str:
    """Pretty print JSON string."""
    data = json.loads(json_str)
    return json.dumps(data, indent=2)`,
  },
  {
    name: "Date Calculator",
    description: "Calculate date differences",
    code: `def days_between(date1: str, date2: str) -> str:
    """Calculate days between two dates (YYYY-MM-DD format)."""
    d1 = datetime.strptime(date1, "%Y-%m-%d")
    d2 = datetime.strptime(date2, "%Y-%m-%d")
    delta = abs((d2 - d1).days)
    return f"{delta} days"`,
  },
];

export function ToolCreateWizard({ onClose, onSuccess, className }: ToolCreateWizardProps) {
  const [step, setStep] = useState<WizardStep>("basics");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [code, setCode] = useState(CODE_TEMPLATE);
  const [category, setCategory] = useState<ToolCategory>("custom");
  const [allowedAgents, setAllowedAgents] = useState<string[]>([]);

  const currentStepIndex = STEPS.findIndex((s) => s.id === step);

  const goNext = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < STEPS.length) {
      setStep(STEPS[nextIndex].id);
    }
  };

  const goPrev = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setStep(STEPS[prevIndex].id);
    }
  };

  const validateBasics = (): boolean => {
    if (!name.trim()) return false;
    if (!/^[a-z][a-z0-9_]*$/.test(name)) return false;
    if (!description.trim()) return false;
    return true;
  };

  const validateCode = (): boolean => {
    if (!code.trim()) return false;
    // Basic check that code defines a function with the tool name
    return code.includes(`def ${name}(`);
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      const request: ToolCreateRequest = {
        name,
        description,
        code,
        category,
        allowed_agents: allowedAgents.length > 0 ? allowedAgents : undefined,
      };

      await createTool(request);
      onSuccess?.(name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create tool");
    } finally {
      setLoading(false);
    }
  };

  const applyExample = (example: (typeof CODE_EXAMPLES)[0]) => {
    setName(example.name.toLowerCase().replace(/\s+/g, "_"));
    setDescription(example.description);
    setCode(example.code);
  };

  return (
    <div
      className={cn(
        "bg-slate-900 border border-slate-800 rounded-xl overflow-hidden flex flex-col",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-pink-500/20 to-purple-500/20 flex items-center justify-center">
            <Wand2 size={20} className="text-pink-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-200">Create Custom Tool</h2>
            <p className="text-xs text-slate-500 font-mono">
              Step {currentStepIndex + 1} of {STEPS.length}
            </p>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {/* Progress steps */}
      <div className="flex items-center justify-center gap-2 p-4 border-b border-slate-800 bg-slate-900/50">
        {STEPS.map((s, i) => (
          <div key={s.id} className="flex items-center">
            <button
              onClick={() => i <= currentStepIndex && setStep(s.id)}
              disabled={i > currentStepIndex}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors",
                i === currentStepIndex
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                  : i < currentStepIndex
                  ? "text-emerald-400 cursor-pointer hover:bg-slate-800"
                  : "text-slate-600 cursor-not-allowed"
              )}
            >
              {i < currentStepIndex ? (
                <Check size={14} className="text-emerald-400" />
              ) : (
                s.icon
              )}
              <span className="font-medium">{s.label}</span>
            </button>
            {i < STEPS.length - 1 && (
              <ChevronRight size={14} className="text-slate-600 mx-1" />
            )}
          </div>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Step: Basics */}
        {step === "basics" && (
          <div className="space-y-6 max-w-2xl mx-auto">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Tool Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_"))}
                placeholder="my_custom_tool"
                className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg py-3 px-4 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 focus:border-cyan-500/50 font-mono"
              />
              <p className="mt-1 text-xs text-slate-500">
                Use snake_case (lowercase letters, numbers, underscores)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this tool does..."
                rows={3}
                className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg py-3 px-4 text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500/30 focus:border-cyan-500/50 resize-none"
              />
            </div>

            {/* Quick examples */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb size={14} className="text-amber-400" />
                <span className="text-sm font-medium text-slate-300">Quick Start Examples</span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {CODE_EXAMPLES.map((example) => (
                  <button
                    key={example.name}
                    onClick={() => applyExample(example)}
                    className="p-3 bg-slate-800/30 border border-slate-700/50 rounded-lg text-left hover:bg-slate-800/50 hover:border-slate-600 transition-all group"
                  >
                    <p className="text-sm font-medium text-slate-300 group-hover:text-cyan-400 transition-colors">
                      {example.name}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">{example.description}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step: Code */}
        {step === "code" && (
          <div className="space-y-4 max-w-3xl mx-auto">
            <div className="flex items-start gap-3 p-4 bg-cyan-500/5 border border-cyan-500/20 rounded-lg">
              <Info size={16} className="text-cyan-400 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-slate-400">
                <p className="font-medium text-cyan-400 mb-1">Code Requirements</p>
                <ul className="list-disc list-inside space-y-1 text-xs">
                  <li>
                    Define a function named <code className="text-cyan-400">{name || "your_tool_name"}</code>
                  </li>
                  <li>Add type hints for parameters and return value</li>
                  <li>Return a string result</li>
                  <li>Available modules: math, json, re, datetime</li>
                </ul>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-slate-300">Python Code</label>
                <button
                  onClick={() => navigator.clipboard.writeText(code)}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <Copy size={12} />
                  <span>Copy</span>
                </button>
              </div>
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                rows={16}
                spellCheck={false}
                className="w-full bg-slate-950 border border-slate-700/50 rounded-lg py-4 px-4 text-slate-200 font-mono text-sm focus:outline-none focus:ring-1 focus:ring-cyan-500/30 focus:border-cyan-500/50 resize-none leading-relaxed"
              />

              {name && !code.includes(`def ${name}(`) && (
                <p className="mt-2 text-xs text-amber-400 flex items-center gap-1">
                  <AlertCircle size={12} />
                  Function name should match tool name: <code>def {name}(...)</code>
                </p>
              )}
            </div>
          </div>
        )}

        {/* Step: Config */}
        {step === "config" && (
          <div className="space-y-6 max-w-2xl mx-auto">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Category
              </label>
              <div className="grid grid-cols-4 gap-2">
                {(Object.keys(CATEGORY_INFO) as ToolCategory[]).map((cat) => {
                  const info = CATEGORY_INFO[cat];
                  return (
                    <button
                      key={cat}
                      onClick={() => setCategory(cat)}
                      className={cn(
                        "p-3 rounded-lg border text-left transition-all",
                        category === cat
                          ? `${info.bgColor} border-current ${info.color}`
                          : "bg-slate-800/30 border-slate-700/50 text-slate-400 hover:border-slate-600"
                      )}
                    >
                      <p className="text-sm font-medium">{info.label}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-3">
                Allowed Agents
                <span className="text-slate-500 font-normal ml-2">(leave empty for all)</span>
              </label>
              <div className="flex flex-wrap gap-2">
                {AGENT_TYPES.map((agent) => (
                  <button
                    key={agent}
                    onClick={() =>
                      setAllowedAgents((prev) =>
                        prev.includes(agent) ? prev.filter((a) => a !== agent) : [...prev, agent]
                      )
                    }
                    className={cn(
                      "px-3 py-2 rounded-lg border text-sm font-mono transition-all",
                      allowedAgents.includes(agent)
                        ? "bg-emerald-500/20 border-emerald-500/30 text-emerald-400"
                        : "bg-slate-800/30 border-slate-700/50 text-slate-400 hover:border-slate-600"
                    )}
                  >
                    {agent}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Step: Review */}
        {step === "review" && (
          <div className="space-y-6 max-w-2xl mx-auto">
            <div className="bg-slate-800/30 rounded-lg border border-slate-700/50 overflow-hidden">
              <div className="px-4 py-3 bg-slate-800/50 border-b border-slate-700/50">
                <h3 className="text-sm font-medium text-slate-300">Tool Summary</h3>
              </div>

              <div className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Name</span>
                  <span className="font-mono text-cyan-400">{name}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Category</span>
                  <span
                    className={cn(
                      "px-2 py-1 rounded text-xs font-mono",
                      CATEGORY_INFO[category].bgColor,
                      CATEGORY_INFO[category].color
                    )}
                  >
                    {CATEGORY_INFO[category].label}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">Agents</span>
                  <span className="text-slate-300 font-mono text-sm">
                    {allowedAgents.length > 0 ? allowedAgents.join(", ") : "All agents"}
                  </span>
                </div>

                <div>
                  <span className="text-sm text-slate-400">Description</span>
                  <p className="mt-1 text-slate-300 text-sm">{description}</p>
                </div>

                <div>
                  <span className="text-sm text-slate-400">Code Preview</span>
                  <pre className="mt-2 p-3 bg-slate-950 rounded-lg text-xs font-mono text-slate-400 overflow-x-auto max-h-48">
                    {code.slice(0, 500)}
                    {code.length > 500 && "..."}
                  </pre>
                </div>
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                <AlertCircle size={16} className="text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-red-400">Creation Failed</p>
                  <p className="text-xs text-red-400/80 mt-1">{error}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between p-4 border-t border-slate-800 bg-slate-950/50">
        <button
          onClick={goPrev}
          disabled={currentStepIndex === 0}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            currentStepIndex === 0
              ? "text-slate-600 cursor-not-allowed"
              : "text-slate-300 hover:bg-slate-800"
          )}
        >
          <ChevronLeft size={16} />
          <span>Back</span>
        </button>

        {step === "review" ? (
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center gap-2 px-6 py-2 rounded-lg bg-gradient-to-r from-cyan-600 to-blue-600 text-white text-sm font-medium hover:from-cyan-500 hover:to-blue-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/20"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Creating...</span>
              </>
            ) : (
              <>
                <Sparkles size={16} />
                <span>Create Tool</span>
              </>
            )}
          </button>
        ) : (
          <button
            onClick={goNext}
            disabled={
              (step === "basics" && !validateBasics()) ||
              (step === "code" && !validateCode())
            }
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 text-sm font-medium hover:bg-cyan-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>Continue</span>
            <ChevronRight size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
