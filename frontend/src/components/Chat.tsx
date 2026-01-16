import { useState, useEffect, useRef } from 'react';
import { getSessions, createSession, sendMessage, getSession, deleteSession } from '../api';
import { cn } from '../lib/utils';
import { MessageSquare, Send, Plus, Loader2, Trash2 } from 'lucide-react';

interface Message {
    id: number;
    role: string;
    content: string;
}

interface Session {
    id: number;
    title: string;
}

export default function Chat() {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

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
            <div className="w-64 border-r border-slate-800 p-4 flex flex-col">
                <button
                    onClick={handleNewChat}
                    className="flex items-center gap-2 w-full p-2 bg-slate-800 hover:bg-slate-700 rounded-md transition-colors text-sm font-medium"
                >
                    <Plus size={16} /> New Research Task
                </button>

                <div className="mt-4 flex-1 overflow-y-auto space-y-1">
                    {sessions.map(session => (
                        <button
                            key={session.id}
                            onClick={() => setCurrentSessionId(session.id)}
                            className={cn(
                                "flex items-center justify-between w-full text-left p-2 rounded-md text-sm transition-colors group",
                                currentSessionId === session.id ? "bg-slate-800 text-blue-400" : "hover:bg-slate-800/50 text-slate-400"
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
            </div>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col">
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-slate-500 flex-col gap-2">
                            <MessageSquare size={48} className="opacity-20" />
                            <p>Select a task or start a new one to begin research.</p>
                        </div>
                    ) : (
                        messages.map((msg) => (
                            <div
                                key={msg.id}
                                className={cn(
                                    "flex flex-col max-w-3xl mx-auto p-4 rounded-lg",
                                    msg.role === 'user' ? "bg-slate-800 items-end" : "bg-slate-900 items-start"
                                )}
                            >
                                <div className="flex items-center gap-2 mb-1">
                                    <span className={cn("text-xs font-bold uppercase", msg.role === 'user' ? "text-blue-400" : "text-green-400")}>{msg.role}</span>
                                </div>
                                <div className="prose prose-invert prose-sm whitespace-pre-wrap">
                                    {msg.content}
                                </div>
                            </div>
                        ))
                    )}
                    <div ref={bottomRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 border-t border-slate-800 bg-slate-900">
                    <div className="max-w-3xl mx-auto relative flex items-center">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && !loading && handleSend()}
                            placeholder="What do you want to research?"
                            disabled={loading || !currentSessionId}
                            className="w-full bg-slate-800 border-none rounded-lg py-3 px-4 pr-12 text-slate-200 placeholder-slate-500 focus:ring-1 focus:ring-blue-500"
                        />
                        <button
                            onClick={handleSend}
                            disabled={loading || !currentSessionId || !input.trim()}
                            className="absolute right-2 p-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 rounded-md transition-colors"
                        >
                            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
