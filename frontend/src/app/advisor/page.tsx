"use client";

import { useState } from "react";
import { Mic, Phone, Send, Activity, X } from "lucide-react";
import { cn } from "@/lib/utils";

type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
  type?: "text" | "portfolio_card" | "alert_card";
};

export default function AdvisorPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [isHindi, setIsHindi] = useState(false);

  const starters = [
    "How is my portfolio?",
    "Invest ₹50,000 for 5 years",
    "Simulate 2008 crash",
    "Why did you suggest gold?"
  ];

  const handleSend = (text: string) => {
    if (!text.trim()) return;
    
    setMessages(prev => [...prev, { id: Date.now().toString(), role: "user", content: text }]);
    setInput("");

    // Simulate AI typing and response
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        id: (Date.now() + 1).toString(), 
        role: "ai", 
        content: "I've analyzed your portfolio. It's performing well, up 2.6% this month. However, your equity exposure is slightly concentrated in RELIANCE." 
      }]);
    }, 1500);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] md:h-[calc(100vh-40px)] animate-in fade-in duration-500 relative bg-navy -mx-4 md:-mx-8 md:-mt-8 px-4 md:px-8 pt-4 md:pt-8 rounded-xl overflow-hidden">
      
      {/* Voice Active Overlay */}
      {isVoiceActive && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-navy/95 backdrop-blur-xl animate-in fade-in duration-300">
          <button 
            onClick={() => setIsVoiceActive(false)}
            className="absolute top-6 right-6 p-2 rounded-full bg-slate-800 text-text-secondary hover:text-white transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
          
          <div className="w-32 h-32 mb-12 relative flex items-center justify-center">
            {/* Pulsing rings */}
            <div className="absolute inset-[-50%] bg-blue-500/20 rounded-full animate-[ping_2s_ease-out_infinite]" />
            <div className="absolute inset-[-20%] bg-blue-500/30 rounded-full animate-[ping_1.5s_ease-out_infinite]" />
            
            <div className="relative z-10 w-24 h-24 bg-blue-600 rounded-full flex items-center justify-center shadow-[0_0_50px_rgba(59,130,246,0.6)]">
              <Mic className="w-10 h-10 text-white" />
            </div>
          </div>
          
          <h2 className="text-3xl font-bold text-white mb-4 text-center">Listening...</h2>
          <p className="text-text-secondary">Speak your financial question naturally</p>

          <div className="flex items-end gap-1 h-12 mt-12 w-48 justify-center">
             {[...Array(12)].map((_, i) => (
                <div 
                  key={i} 
                  className="w-2 bg-blue-500 rounded-full"
                  style={{ 
                    height: `${20 + Math.random() * 80}%`,
                    animation: `pulse ${0.5 + Math.random() * 0.5}s ease-in-out infinite alternate`
                  }} 
                />
             ))}
          </div>
        </div>
      )}

      {/* Top Bar */}
      <div className="flex-none flex items-center justify-between pb-4 border-b border-border-subtle bg-navy z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center relative">
            <Activity className="w-5 h-5 text-white" />
            <div className="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-emerald-500 border-2 border-navy" />
          </div>
          <div>
            <h1 className="text-lg md:text-xl font-bold text-white leading-tight">FinVoice AI</h1>
            <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-accent">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              Live Advisory
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsHindi(!isHindi)}
            className="px-3 py-1.5 rounded-full bg-slate-800 border border-border-subtle text-text-secondary text-xs font-bold hover:text-white transition-colors"
          >
            {isHindi ? "English" : "Switch to Hindi"}
          </button>
          <button className="w-10 h-10 rounded-full bg-green-500/10 border border-green-500/30 text-green-500 flex items-center justify-center hover:bg-green-500/20 transition-colors">
            <Phone className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Chat Area Scrollable */}
      <div className="flex-1 overflow-y-auto w-full max-w-3xl mx-auto py-6 flex flex-col gap-6 px-2 pr-4 scroll-smooth">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center">
            <div className="w-16 h-16 rounded-2xl bg-slate-800 border border-border-subtle flex items-center justify-center mb-6">
              <Activity className="w-8 h-8 text-blue-500" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">How can I help you today?</h2>
            <p className="text-text-secondary mb-10 text-center">Institutional-grade answers to all your portfolio questions.</p>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
              {starters.map(s => (
                <button 
                  key={s}
                  onClick={() => handleSend(s)}
                  className="p-4 rounded-xl bg-slate-800 border border-border-subtle text-left text-sm font-medium text-text-secondary hover:text-white hover:border-blue-500/50 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} className={cn("flex w-full", msg.role === "user" ? "justify-end" : "justify-start")}>
              {msg.role === "ai" && (
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center shrink-0 mr-3 mt-1">
                  <Activity className="w-4 h-4 text-white" />
                </div>
              )}
              <div 
                className={cn(
                  "px-5 py-3.5 max-w-[85%] sm:max-w-[75%]",
                  msg.role === "user" 
                    ? "bg-blue-600 text-white rounded-2xl rounded-tr-sm" 
                    : "bg-[#1A2235] text-text-primary rounded-2xl rounded-tl-sm border border-[#1E2D45] leading-relaxed shadow-sm"
                )}
              >
                {msg.content}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Bottom Input Area */}
      <div className="flex-none bg-navy pt-2 pb-6 shrink-0 z-10 w-full max-w-4xl mx-auto">
        <div className="relative flex items-center gap-2">
          <button 
            onClick={() => setIsVoiceActive(true)}
            className="w-14 h-14 rounded-full bg-slate-800 border border-border-subtle flex items-center justify-center flex-shrink-0 text-text-secondary hover:text-white hover:border-blue-500 transition-colors"
          >
            <Mic className="w-6 h-6" />
          </button>
          
          <div className="relative flex-1">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend(input)}
              placeholder="Ask anything about your portfolio..."
              className="w-full pl-6 pr-14 h-14 rounded-full bg-slate-800 border border-border-subtle text-white focus:outline-none focus:border-blue-500 transition-colors"
            />
            <button 
              onClick={() => handleSend(input)}
              disabled={!input.trim()}
              className="absolute right-2 top-2 bottom-2 w-10 rounded-full flex items-center justify-center bg-blue-600 text-white disabled:opacity-50 disabled:bg-slate-700 transition-colors"
            >
              <Send className="w-4 h-4 ml-0.5" />
            </button>
          </div>
        </div>
        <p className="text-center mt-3 text-[10px] text-text-muted">
          FinVoice is a decision-support tool. Not SEBI-registered advice.
        </p>
      </div>
    </div>
  );
}
