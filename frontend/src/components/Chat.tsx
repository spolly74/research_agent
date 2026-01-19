import { useState, useEffect, useRef } from 'react';
import { getSessions, createSession, sendMessage, getSession, deleteSession } from '../api';
import { cn } from '../lib/utils';
import { MessageSquare, Send, Plus, Loader2, Trash2, Activity, BookOpen, Maximize2 } from 'lucide-react';
import { StatusDashboard } from './ExecutionStatus';
import { ReportViewer } from './ReportViewer';

interface Message {
    id: number;
    role: string;
    content: string;
}

interface Session {
    id: number;
    title: string;
}

// Detect if content looks like a report (has markdown headers and is long enough)
function isReportContent(content: string): boolean {
    const hasHeaders = /^#{1,3}\s+.+$/m.test(content);
    const wordCount = content.split(/\s+/).length;
    return hasHeaders && wordCount > 200;
}

export default function Chat() {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [showStatus, setShowStatus] = useState(true);
    const [expandedReport, setExpandedReport] = useState<number | null>(null);
    const bottomRef = useRef<HTMLDivElement>(null);

    // Session ID format used by backend for tracking
    const trackingSessionId = currentSessionId ? `chat-${currentSessionId}` : null;

    useEffect(() => {
        loadSessions();
    }, []);

    useEffect(() => {
        if (currentSessionId) {
            loadMessages(currentSessionId);
        }
    }, [currentSessionId]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const loadSessions = async () => {
        const data = await getSessions();
        setSessions(data);
        if (data.length > 0 && !currentSessionId) {
            setCurrentSessionId(data[0].id);
        }
    };

    const loadMessages = async (id: number) => {
        const data = await getSession(id);
        if (data && data.messages) {
            setMessages(data.messages);
        }
    };

    const handleNewChat = async () => {
        const session = await createSession();
        setSessions([session, ...sessions]);
        setCurrentSessionId(session.id);
        setMessages([]);
    };

    const handleDelete = async (e: React.MouseEvent, id: number) => {
        e.stopPropagation();
        if (confirm("Are you sure you want to delete this chat?")) {
            await deleteSession(id);
            setSessions(prev => prev.filter(s => s.id !== id));
            if (currentSessionId === id) {
                setCurrentSessionId(null);
                setMessages([]);
            }
        }
    };

    const handleSend = async () => {
        if (!input.trim() || !currentSessionId) return;

        const userMsg = { id: Date.now(), role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput("");
        setLoading(true);
        setShowStatus(true); // Show status dashboard when processing

        try {
            await sendMessage(currentSessionId, userMsg.content);
            await loadMessages(currentSessionId);
        } catch (error) {
            console.error("Failed to send message", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex h-screen bg-slate-900 text-slate-100 font-sans">
            {/* Sidebar */}
            <div className="w-64 border-r border-slate-800 p-4 flex flex-col bg-slate-950/50">
                <button
                    onClick={handleNewChat}
                    className="flex items-center gap-2 w-full p-2.5 bg-gradient-to-r from-cyan-600/20 to-blue-600/20 hover:from-cyan-600/30 hover:to-blue-600/30 border border-cyan-500/30 rounded-lg transition-all text-sm font-medium text-cyan-400"
                >
                    <Plus size={16} /> New Research Task
                </button>

                <div className="mt-4 flex-1 overflow-y-auto space-y-1">
                    {sessions.map(session => (
                        <button
                            key={session.id}
                            onClick={() => setCurrentSessionId(session.id)}
                            className={cn(
                                "flex items-center justify-between w-full text-left p-2.5 rounded-lg text-sm transition-all group",
                                currentSessionId === session.id
                                    ? "bg-slate-800/80 text-cyan-400 border border-cyan-500/20"
                                    : "hover:bg-slate-800/50 text-slate-400 border border-transparent"
                            )}
                        >
                            <div className="flex items-center truncate">
                                <MessageSquare size={14} className="inline mr-2 flex-shrink-0" />
                                <span className="truncate">{session.title}</span>
                            </div>
                            <button
                                onClick={(e) => handleDelete(e, session.id)}
                                className={cn(
                                    "p-1 rounded hover:bg-slate-700/50 text-slate-500 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100",
                                    currentSessionId === session.id ? "opacity-100" : ""
                                )}
                            >
                                <Trash2 size={13} />
                            </button>
                        </button>
                    ))}
                </div>

                {/* Status toggle */}
                {loading && (
                    <button
                        onClick={() => setShowStatus(!showStatus)}
                        className={cn(
                            "mt-2 flex items-center gap-2 w-full p-2 rounded-lg text-xs font-mono transition-colors",
                            showStatus
                                ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                                : "bg-slate-800/50 text-slate-500 border border-slate-700/50"
                        )}
                    >
                        <Activity size={12} className={showStatus ? "animate-pulse" : ""} />
                        <span>{showStatus ? "Status: ON" : "Status: OFF"}</span>
                    </button>
                )}
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col">
                {/* Status Dashboard - Shows when processing */}
                {loading && showStatus && trackingSessionId && (
                    <div className="border-b border-slate-700/50 p-4 bg-slate-900/50">
                        <StatusDashboard
                            sessionId={trackingSessionId}
                            isProcessing={loading}
                        />
                    </div>
                )}

                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-slate-500 flex-col gap-4">
                            <div className="relative">
                                <MessageSquare size={64} className="opacity-10" />
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <div className="w-4 h-4 rounded-full bg-cyan-500/20 animate-ping" />
                                </div>
                            </div>
                            <div className="text-center">
                                <p className="text-lg font-medium text-slate-400">Research Agent Ready</p>
                                <p className="text-sm text-slate-600 mt-1">Start a new task or select an existing one</p>
                            </div>
                        </div>
                    ) : (
                        messages.map((msg) => {
                            const isReport = msg.role === 'assistant' && isReportContent(msg.content);
                            const isExpanded = expandedReport === msg.id;

                            // Show fullscreen ReportViewer when expanded
                            if (isExpanded && isReport) {
                                return (
                                    <div key={msg.id} className="fixed inset-0 z-50 bg-slate-950/95 backdrop-blur-sm p-4">
                                        <ReportViewer
                                            content={msg.content}
                                            className="h-full"
                                            onClose={() => setExpandedReport(null)}
                                        />
                                    </div>
                                );
                            }

                            return (
                                <div
                                    key={msg.id}
                                    className={cn(
                                        "flex flex-col max-w-3xl mx-auto p-4 rounded-xl transition-all",
                                        msg.role === 'user'
                                            ? "bg-gradient-to-r from-slate-800 to-slate-800/80 border border-slate-700/50"
                                            : "bg-gradient-to-r from-slate-900 to-slate-900/80 border border-slate-700/30"
                                    )}
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className={cn(
                                                "w-2 h-2 rounded-full",
                                                msg.role === 'user' ? "bg-blue-500" : "bg-emerald-500"
                                            )} />
                                            <span className={cn(
                                                "text-xs font-mono font-semibold uppercase tracking-wider",
                                                msg.role === 'user' ? "text-blue-400" : "text-emerald-400"
                                            )}>
                                                {msg.role}
                                            </span>
                                        </div>

                                        {/* Report view button for assistant reports */}
                                        {isReport && (
                                            <button
                                                onClick={() => setExpandedReport(msg.id)}
                                                className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 transition-colors text-xs font-medium"
                                            >
                                                <BookOpen size={12} />
                                                <span>View Report</span>
                                                <Maximize2 size={10} />
                                            </button>
                                        )}
                                    </div>

                                    {/* Content preview or full content */}
                                    {isReport ? (
                                        <div className="relative">
                                            <div className="prose prose-invert prose-sm whitespace-pre-wrap text-slate-300 max-h-64 overflow-hidden">
                                                {msg.content.slice(0, 500)}
                                                {msg.content.length > 500 && '...'}
                                            </div>
                                            <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-slate-900 to-transparent pointer-events-none" />
                                            <div className="mt-2 pt-2 border-t border-slate-700/50 flex items-center justify-between">
                                                <span className="text-xs font-mono text-slate-500">
                                                    {msg.content.split(/\s+/).length.toLocaleString()} words
                                                </span>
                                                <button
                                                    onClick={() => setExpandedReport(msg.id)}
                                                    className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                                                >
                                                    Read full report →
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="prose prose-invert prose-sm whitespace-pre-wrap text-slate-300">
                                            {msg.content}
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    )}
                    <div ref={bottomRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 border-t border-slate-700/50 bg-gradient-to-t from-slate-950 to-slate-900">
                    <div className="max-w-3xl mx-auto relative flex items-center">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && !loading && handleSend()}
                            placeholder="What do you want to research?"
                            disabled={loading || !currentSessionId}
                            className={cn(
                                "w-full bg-slate-800/80 border border-slate-700/50 rounded-xl py-3.5 px-5 pr-14",
                                "text-slate-200 placeholder-slate-500",
                                "focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500/50 focus:outline-none",
                                "transition-all duration-200",
                                "disabled:opacity-50 disabled:cursor-not-allowed"
                            )}
                        />
                        <button
                            onClick={handleSend}
                            disabled={loading || !currentSessionId || !input.trim()}
                            className={cn(
                                "absolute right-2 p-2.5 rounded-lg transition-all duration-200",
                                "bg-gradient-to-r from-cyan-600 to-blue-600",
                                "hover:from-cyan-500 hover:to-blue-500",
                                "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-cyan-600 disabled:hover:to-blue-600",
                                "shadow-lg shadow-cyan-500/20"
                            )}
                        >
                            {loading ? (
                                <Loader2 size={16} className="animate-spin text-white" />
                            ) : (
                                <Send size={16} className="text-white" />
                            )}
                        </button>
                    </div>

                    {/* Processing indicator */}
                    {loading && (
                        <div className="max-w-3xl mx-auto mt-3 flex items-center gap-2 text-xs font-mono text-cyan-500">
                            <div className="flex gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                                <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                                <span className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                            </div>
                            <span>Processing research request...</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
