import React, { useState, useRef, useEffect, memo } from 'react';
import { useMessageStore, Message } from '../store/useMessageStore';
import { useStreamingResponse } from '../hooks/useStreamingResponse';
import { Send, BrainCircuit, Shield, User } from 'lucide-react';

interface ChatViewProps {
  tabId: string;
}

const MessageItem = memo(({ msg }: { msg: Message }) => {
  return (
    <div
      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[85%] rounded-2xl p-4 shadow-lg transition-all ${
          msg.role === 'user'
            ? 'bg-blue-600 text-white rounded-tr-none'
            : msg.isThought
            ? 'bg-slate-800/50 border border-slate-700/50 text-slate-400 italic rounded-tl-none'
            : 'bg-slate-800 border border-slate-700 text-slate-100 rounded-tl-none'
        }`}
      >
        <div className="flex items-center gap-2 mb-2">
          <div className={`p-1 rounded-md ${
            msg.role === 'user' 
              ? 'bg-blue-500' 
              : msg.isThought 
              ? 'bg-slate-700' 
              : 'bg-emerald-500/20'
          }`}>
            {msg.role === 'user' ? (
              <User size={14} className="text-white" />
            ) : msg.isThought ? (
              <BrainCircuit size={14} className="text-purple-400" />
            ) : (
              <Shield size={14} className="text-emerald-400" />
            )}
          </div>
          <span className="text-[10px] font-bold uppercase tracking-widest opacity-60">
            {msg.role === 'user' ? 'Security Analyst' : msg.isThought ? 'Thought Trace' : 'Orchestrator'}
          </span>
        </div>
        
        <div className="whitespace-pre-wrap text-sm leading-relaxed">
          {msg.content || (msg.isThought ? 'Thinking...' : '...')}
        </div>
      </div>
    </div>
  );
});

export const ChatView: React.FC<ChatViewProps> = ({ tabId }) => {
  const [input, setInput] = useState('');
  const messages = useMessageStore((state) => state.messages[tabId] || []);
  const addMessage = useMessageStore((state) => state.addMessage);
  const { stream } = useStreamingResponse(tabId);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll mechanism
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Math.random().toString(36).substring(7),
      query_id: Math.random().toString(36).substring(7),
      role: 'user' as const,
      content: input,
      isThought: false,
      timestamp: Date.now(),
    };

    addMessage(tabId, userMessage);
    const query = input;
    setInput('');
    
    // Trigger streaming response
    await stream(query);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100 font-sans">
      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
            <Shield size={48} className="opacity-20" />
            <p className="text-lg">Start a security orchestration cycle</p>
          </div>
        )}
        
        {messages.map((msg) => (
          <MessageItem key={msg.id} msg={msg} />
        ))}
        <div ref={scrollRef} className="h-4" />
      </div>
...

      {/* Input Area */}
      <div className="p-6 bg-slate-900 border-t border-slate-800">
        <form 
          onSubmit={handleSend}
          className="relative max-w-4xl mx-auto"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe an indicator or ask a security question..."
            className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-4 pr-14 py-4 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-inner"
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="absolute right-2 top-2 bottom-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:opacity-50 text-white px-4 rounded-lg transition-all flex items-center justify-center group"
          >
            <Send size={18} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </form>
        <p className="text-[10px] text-center mt-3 text-slate-600 uppercase tracking-tighter">
          Security Orchestrator AI may provide suggestions. Verify critical remediations.
        </p>
      </div>
    </div>
  );
};
