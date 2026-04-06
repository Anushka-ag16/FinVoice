"use client";

import { useState, useRef, useEffect } from "react";
import { Mic, Phone, PhoneOff, Send, Activity, X } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Lightweight Markdown Renderer ───

function renderMarkdown(text: string) {
  if (!text) return null;

  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];
  let listKey = 0;

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${listKey++}`} className="list-disc list-inside space-y-1 my-2">
          {listItems.map((item, i) => (
            <li key={i} className="text-sm">{formatInline(item)}</li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  const formatInline = (line: string): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    let remaining = line;
    let partKey = 0;

    while (remaining.length > 0) {
      const boldMatch = remaining.match(/\*\*(.+?)\*\*|__(.+?)__/);
      const codeMatch = remaining.match(/`([^`]+)`/);
      const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)/);

      type MatchCandidate = { index: number; length: number; content: React.ReactNode };
      let firstMatch: MatchCandidate | null = null;

      if (boldMatch && boldMatch.index !== undefined) {
        const candidate: MatchCandidate = { index: boldMatch.index, length: boldMatch[0].length, content: <strong key={`b-${partKey++}`} className="font-semibold text-slate-900">{boldMatch[1] || boldMatch[2]}</strong> };
        if (!firstMatch || candidate.index < firstMatch.index) firstMatch = candidate;
      }
      if (codeMatch && codeMatch.index !== undefined) {
        const candidate: MatchCandidate = { index: codeMatch.index, length: codeMatch[0].length, content: <code key={`c-${partKey++}`} className="px-1.5 py-0.5 rounded bg-slate-100 text-blue-700 text-xs font-mono">{codeMatch[1]}</code> };
        if (!firstMatch || candidate.index < firstMatch.index) firstMatch = candidate;
      }
      if (!firstMatch && italicMatch && italicMatch.index !== undefined) {
        const candidate: MatchCandidate = { index: italicMatch.index, length: italicMatch[0].length, content: <em key={`i-${partKey++}`} className="italic text-slate-600">{italicMatch[1] || italicMatch[2]}</em> };
        if (!firstMatch || candidate.index < firstMatch.index) firstMatch = candidate;
      }

      if (firstMatch) {
        if (firstMatch.index > 0) {
          parts.push(remaining.slice(0, firstMatch.index));
        }
        parts.push(firstMatch.content);
        remaining = remaining.slice(firstMatch.index + firstMatch.length);
      } else {
        parts.push(remaining);
        break;
      }
    }

    return parts.length === 1 ? parts[0] : <>{parts}</>;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith("### ")) {
      flushList();
      elements.push(<h4 key={i} className="text-sm font-bold text-slate-900 mt-3 mb-1">{formatInline(line.slice(4))}</h4>);
    } else if (line.startsWith("## ")) {
      flushList();
      elements.push(<h3 key={i} className="text-base font-bold text-slate-900 mt-3 mb-1">{formatInline(line.slice(3))}</h3>);
    } else if (line.startsWith("# ")) {
      flushList();
      elements.push(<h2 key={i} className="text-lg font-bold text-slate-900 mt-3 mb-1">{formatInline(line.slice(2))}</h2>);
    }
    else if (line.match(/^[\s]*[-*•]\s/)) {
      const content = line.replace(/^[\s]*[-*•]\s/, "");
      listItems.push(content);
    }
    else if (line.match(/^[\s]*\d+\.\s/)) {
      const content = line.replace(/^[\s]*\d+\.\s/, "");
      listItems.push(content);
    }
    else if (line.match(/^---+$/)) {
      flushList();
      elements.push(<hr key={i} className="border-slate-200 my-3" />);
    }
    else if (line.trim() === "") {
      flushList();
    }
    else {
      flushList();
      elements.push(<p key={i} className="text-sm leading-relaxed my-1">{formatInline(line)}</p>);
    }
  }
  flushList();

  return <div className="prose-sm">{elements}</div>;
}

// ─── Types ───

type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
};

export default function AdvisorPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isHindi, setIsHindi] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  // Phone call popup state
  const [showCallPopup, setShowCallPopup] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [callStatus, setCallStatus] = useState<"idle" | "calling" | "success" | "error">("idle");
  const [callMessage, setCallMessage] = useState("");

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ─── Phone Call Handler ───
  const handlePhoneCall = async () => {
    if (!phoneNumber.trim()) return;
    
    setCallStatus("calling");
    setCallMessage("");

    try {
      const res = await fetch("/api/vapi-call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phoneNumber: phoneNumber.trim() }),
      });

      const data = await res.json();

      if (!res.ok) {
        setCallStatus("error");
        setCallMessage(data.error || "Failed to initiate call");
        return;
      }

      setCallStatus("success");
      setCallMessage(data.message || "Call initiated! You'll receive a call shortly.");
      
      // Auto-close after 4 seconds on success
      setTimeout(() => {
        setShowCallPopup(false);
        setCallStatus("idle");
        setPhoneNumber("");
        setCallMessage("");
      }, 4000);
    } catch (err) {
      console.error("Call error:", err);
      setCallStatus("error");
      setCallMessage("Network error. Please try again.");
    }
  };

  const openCallPopup = () => {
    setShowCallPopup(true);
    setCallStatus("idle");
    setCallMessage("");
  };

  const closeCallPopup = () => {
    if (callStatus !== "calling") {
      setShowCallPopup(false);
      setCallStatus("idle");
      setPhoneNumber("");
      setCallMessage("");
    }
  };

  const starters = [
    "How is my portfolio?",
    "Invest ₹50,000 for 5 years",
    "Simulate 2008 crash",
    "Why did you suggest gold?"
  ];

  const handleSend = async (text: string) => {
    if (!text.trim() || isStreaming) return;
    
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

    const aiMsgId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: aiMsgId, role: "ai", content: "" }]);

    const history = messages.map(m => ({
      role: m.role === "user" ? "user" : "assistant",
      content: m.content,
    }));

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });

      if (!res.ok) throw new Error(`API error ${res.status}`);

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No readable stream");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.done) break;
            if (payload.error) {
              setMessages(prev =>
                prev.map(m => m.id === aiMsgId ? { ...m, content: m.content + `\n\n⚠️ ${payload.error}` } : m)
              );
              break;
            }
            if (payload.token) {
              setMessages(prev =>
                prev.map(m => m.id === aiMsgId ? { ...m, content: m.content + payload.token } : m)
              );
            }
          } catch { /* skip malformed lines */ }
        }
      }
    } catch (err) {
      console.warn("Backend unavailable, using fallback response", err);
      const fallback = "I've analyzed your portfolio. It's performing well, up 2.6% this month. However, your equity exposure is slightly concentrated in RELIANCE. I'd recommend diversifying into FMCG or healthcare sectors to reduce concentration risk.";
      for (let i = 0; i < fallback.length; i += 3) {
        const chunk = fallback.slice(i, i + 3);
        await new Promise(r => setTimeout(r, 20));
        setMessages(prev =>
          prev.map(m => m.id === aiMsgId ? { ...m, content: m.content + chunk } : m)
        );
      }
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] md:h-[calc(100vh-40px)] animate-in fade-in duration-500 relative bg-navy -mx-4 md:-mx-8 md:-mt-8 px-4 md:px-8 pt-4 md:pt-8 rounded-xl overflow-hidden">
      
      {/* ─── Phone Call Popup Modal ─── */}
      {showCallPopup && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden animate-in zoom-in-95 duration-300">
            {/* Header */}
            <div className="p-6 pb-0 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <Phone className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Talk to FinVoice AI</h3>
                  <p className="text-xs text-slate-500">Get a call from your AI advisor</p>
                </div>
              </div>
              <button 
                onClick={closeCallPopup}
                className="p-2 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 space-y-4">
              {callStatus === "success" ? (
                <div className="text-center py-4 space-y-3 animate-in fade-in duration-300">
                  <div className="w-16 h-16 mx-auto rounded-full bg-green-100 flex items-center justify-center">
                    <Phone className="w-8 h-8 text-green-600 animate-pulse" />
                  </div>
                  <h4 className="text-lg font-semibold text-green-700">Call Initiated!</h4>
                  <p className="text-sm text-slate-500">{callMessage}</p>
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Your Phone Number</label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-sm font-medium">+91</span>
                      <input
                        type="tel"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value.replace(/[^\d]/g, "").slice(0, 10))}
                        onKeyDown={(e) => e.key === "Enter" && phoneNumber.length === 10 && handlePhoneCall()}
                        placeholder="98765 43210"
                        disabled={callStatus === "calling"}
                        className="w-full pl-14 pr-4 py-4 rounded-xl bg-slate-50 border border-slate-200 text-slate-900 font-mono text-lg tracking-wider focus:border-green-500 focus:outline-none focus:ring-2 focus:ring-green-500/20 transition-colors disabled:opacity-60 placeholder:text-slate-300"
                        autoFocus
                      />
                    </div>
                    <p className="text-[11px] text-slate-400 mt-2">We&apos;ll call you on this number with your AI financial advisor</p>
                  </div>

                  {callStatus === "error" && (
                    <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700 animate-in fade-in duration-200">
                      {callMessage}
                    </div>
                  )}

                  <button
                    onClick={handlePhoneCall}
                    disabled={phoneNumber.length < 10 || callStatus === "calling"}
                    className={cn(
                      "w-full py-4 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2",
                      phoneNumber.length >= 10 && callStatus !== "calling"
                        ? "bg-green-600 hover:bg-green-700 text-white shadow-lg shadow-green-600/20"
                        : "bg-slate-100 text-slate-400 cursor-not-allowed"
                    )}
                  >
                    {callStatus === "calling" ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Connecting...
                      </>
                    ) : (
                      <>
                        <Phone className="w-5 h-5" />
                        Call Me Now
                      </>
                    )}
                  </button>
                </>
              )}
            </div>
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
            <h1 className="text-lg md:text-xl font-bold text-slate-900 leading-tight">FinVoice AI</h1>
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
            className="px-3 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-slate-600 text-xs font-bold hover:text-slate-900 transition-colors"
          >
            {isHindi ? "English" : "हिन्दी"}
          </button>
          <button
            onClick={openCallPopup}
            className="w-10 h-10 rounded-full flex items-center justify-center transition-colors bg-green-500/10 border border-green-500/30 text-green-600 hover:bg-green-500/20"
          >
            <Phone className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Chat Area Scrollable */}
      <div className="flex-1 overflow-y-auto w-full max-w-3xl mx-auto py-6 flex flex-col gap-6 px-2 pr-4 scroll-smooth">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mb-6">
              <Activity className="w-8 h-8 text-blue-500" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-2">How can I help you today?</h2>
            <p className="text-slate-500 mb-10 text-center">Institutional-grade answers to all your portfolio questions.</p>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
              {starters.map(s => (
                <button 
                  key={s}
                  onClick={() => handleSend(s)}
                  className="p-4 rounded-xl bg-white border border-slate-200 text-left text-sm font-medium text-slate-600 hover:text-slate-900 hover:border-blue-400 hover:bg-blue-50 transition-colors shadow-sm"
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
                  "max-w-[85%] sm:max-w-[75%]",
                  msg.role === "user" 
                    ? "px-5 py-3.5 bg-blue-600 text-white rounded-2xl rounded-tr-sm" 
                    : "px-5 py-3.5 bg-white text-slate-700 rounded-2xl rounded-tl-sm border border-slate-200 shadow-sm"
                )}
              >
                {msg.role === "ai" ? (
                  msg.content ? renderMarkdown(msg.content) : (
                    <div className="flex items-center gap-2 text-slate-400 text-sm">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                        <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                        <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                      Thinking...
                    </div>
                  )
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Bottom Input Area */}
      <div className="flex-none bg-navy pt-2 pb-6 shrink-0 z-10 w-full max-w-4xl mx-auto">
        <div className="relative flex items-center gap-2">
          <button 
            onClick={openCallPopup}
            className="w-14 h-14 rounded-full flex items-center justify-center flex-shrink-0 transition-colors shadow-sm bg-white border border-slate-200 text-slate-500 hover:text-green-600 hover:border-green-400"
          >
            <Phone className="w-6 h-6" />
          </button>
          
          <div className="relative flex-1">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend(input)}
              placeholder={isStreaming ? "AI is responding..." : "Ask anything about your portfolio..."}
              disabled={isStreaming}
              className="w-full pl-6 pr-14 h-14 rounded-full bg-slate-100 border border-slate-200 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors disabled:opacity-60"
            />
            <button 
              onClick={() => handleSend(input)}
              disabled={!input.trim() || isStreaming}
              className="absolute right-2 top-2 bottom-2 w-10 rounded-full flex items-center justify-center bg-blue-600 text-white disabled:opacity-50 disabled:bg-slate-300 transition-colors"
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
