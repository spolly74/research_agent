/**
 * ToolManagementPage - Main page for tool management
 * Combines ToolList, ExecutionHistory, and CreateWizard
 */

import { useState } from "react";
import { cn } from "../../lib/utils";
import { ToolList } from "./ToolList";
import { ToolExecutionHistory } from "./ToolExecutionHistory";
import { ToolCreateWizard } from "./ToolCreateWizard";
import {
  Wrench,
  History,
  X,
  Layers,
} from "lucide-react";

interface ToolManagementPageProps {
  className?: string;
}

type ActiveTab = "tools" | "history";

export function ToolManagementPage({ className }: ToolManagementPageProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>("tools");
  const [showCreateWizard, setShowCreateWizard] = useState(false);

  return (
    <div className={cn("flex flex-col h-full bg-slate-950", className)}>
      {/* Header with tabs */}
      <div className="flex-shrink-0 border-b border-slate-800 bg-slate-900/50">
        <div className="flex items-center justify-between px-4 pt-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/20 to-purple-500/20 flex items-center justify-center">
              <Layers size={20} className="text-cyan-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-slate-200">Tool Management</h1>
              <p className="text-xs text-slate-500 font-mono">Manage research agent tools</p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 px-4 pt-4">
          <button
            onClick={() => setActiveTab("tools")}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-t-lg text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === "tools"
                ? "bg-slate-800/50 text-cyan-400 border-cyan-500"
                : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-800/30"
            )}
          >
            <Wrench size={14} />
            <span>Tools</span>
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-t-lg text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === "history"
                ? "bg-slate-800/50 text-cyan-400 border-cyan-500"
                : "text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-800/30"
            )}
          >
            <History size={14} />
            <span>Execution History</span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === "tools" && (
          <ToolList
            onCreateClick={() => setShowCreateWizard(true)}
            className="h-full"
          />
        )}

        {activeTab === "history" && (
          <ToolExecutionHistory className="h-full" />
        )}

        {/* Create wizard overlay */}
        {showCreateWizard && (
          <div className="absolute inset-0 bg-slate-950/90 backdrop-blur-sm flex items-center justify-center p-8 z-50">
            <ToolCreateWizard
              onClose={() => setShowCreateWizard(false)}
              onSuccess={(toolName) => {
                setShowCreateWizard(false);
                // Could trigger a refresh of the tool list here
                console.log(`Tool created: ${toolName}`);
              }}
              className="w-full max-w-4xl max-h-full"
            />
          </div>
        )}
      </div>
    </div>
  );
}
