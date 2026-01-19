import { useState } from 'react'
import Chat from './components/Chat'
import { ToolManagementPage } from './components/ToolManagement'
import { cn } from './lib/utils'
import { MessageSquare, Wrench, Bot } from 'lucide-react'

type AppView = 'chat' | 'tools'

function App() {
    const [view, setView] = useState<AppView>('chat')

    return (
        <div className="w-full h-screen bg-slate-950 flex flex-col">
            {/* Top navigation bar */}
            <nav className="flex-shrink-0 h-12 border-b border-slate-800 bg-slate-900/50 flex items-center px-4">
                <div className="flex items-center gap-2 mr-6">
                    <Bot size={20} className="text-cyan-400" />
                    <span className="font-semibold text-slate-200">Research Agent</span>
                </div>

                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setView('chat')}
                        className={cn(
                            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                            view === 'chat'
                                ? "bg-cyan-500/20 text-cyan-400"
                                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                        )}
                    >
                        <MessageSquare size={14} />
                        <span>Chat</span>
                    </button>
                    <button
                        onClick={() => setView('tools')}
                        className={cn(
                            "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                            view === 'tools'
                                ? "bg-cyan-500/20 text-cyan-400"
                                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                        )}
                    >
                        <Wrench size={14} />
                        <span>Tools</span>
                    </button>
                </div>
            </nav>

            {/* Main content */}
            <div className="flex-1 overflow-hidden">
                {view === 'chat' && <Chat />}
                {view === 'tools' && <ToolManagementPage />}
            </div>
        </div>
    )
}

export default App
