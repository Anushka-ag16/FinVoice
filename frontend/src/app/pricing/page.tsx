"use client";

import { useState } from "react";
import { Check, X, Star, Lock } from "lucide-react";
import { cn } from "@/lib/utils";

export default function PricingPage() {
  const [isAnnual, setIsAnnual] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const features = [
    { name: "Risk Assessment", free: true, pro: true },
    { name: "Portfolio Analysis", free: true, pro: true },
    { name: "Basic Rebalancing", free: true, pro: true },
    { name: "Crash Simulation", free: false, pro: true },
    { name: "Algo Trading Sandbox", free: false, pro: true },
    { name: "AI Voice Advisory (Vapi)", free: false, pro: true },
    { name: "PDF Monthly Reports", free: false, pro: true },
  ];

  return (
    <div className="flex flex-col items-center py-20 animate-in fade-in duration-500 relative min-h-screen z-0">
      
      {/* Payment Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-navy/80 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative z-10 w-full max-w-md bg-[#111827] border border-[#1E2D45] rounded-2xl p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold text-white">Upgrade to Pro</h3>
              <button onClick={() => setShowModal(false)} className="text-text-muted hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-4 rounded-xl bg-slate-800 border border-border-subtle mb-6">
              <div className="flex justify-between items-center mb-2">
                <span className="text-white font-medium">FinVoice Pro ({isAnnual ? 'Annual' : 'Monthly'})</span>
                <span className="font-mono text-white font-bold">₹{isAnnual ? '2,390' : '299'}</span>
              </div>
              <p className="text-xs text-text-secondary">Billed {isAnnual ? 'yearly' : 'monthly'}. Cancel anytime.</p>
            </div>

            <div className="space-y-4 mb-8">
              {/* Dummy Razorpay/Stripe form layout */}
              <div className="h-12 w-full rounded-lg bg-slate-800 border border-border-subtle px-4 flex items-center text-text-muted text-sm">
                Card number, MM/YY, CVC
              </div>
              <div className="h-12 w-full rounded-lg bg-slate-800 border border-border-subtle px-4 flex items-center text-text-muted text-sm">
                Cardholder name
              </div>
            </div>

            <button 
              onClick={() => {
                alert("Payment successful! Welcome to FinVoice Pro.");
                setShowModal(false);
              }}
              className="w-full py-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold shadow-lg transition-colors flex items-center justify-center gap-2 mb-4"
            >
              <Lock className="w-4 h-4" /> Pay ₹{isAnnual ? '2,390' : '299'} Securely
            </button>
            
            <div className="flex items-center justify-center gap-2 text-xs text-text-muted">
              <Lock className="w-3 h-3" /> Secure payment via Razorpay
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <h1 className="text-4xl md:text-5xl font-bold text-white text-center mb-8">
        Choose Your Plan
      </h1>

      <div className="flex items-center gap-3 bg-slate-800 p-1.5 rounded-full border border-border-subtle mb-16 relative">
        <button 
          onClick={() => setIsAnnual(false)}
          className={cn("px-6 py-2.5 rounded-full text-sm font-bold z-10 transition-colors", !isAnnual ? "text-white" : "text-text-secondary hover:text-white")}
        >
          Monthly
        </button>
        <button 
          onClick={() => setIsAnnual(true)}
          className={cn("px-6 py-2.5 rounded-full text-sm font-bold z-10 transition-colors flex items-center gap-2", isAnnual ? "text-white" : "text-text-secondary hover:text-white")}
        >
          Annually <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-accent text-[10px] uppercase tracking-wider">Save 20%</span>
        </button>
        <div 
          className={cn("absolute top-1.5 bottom-1.5 w-[50%] bg-blue-600 rounded-full transition-all duration-300 shadow", isAnnual ? "left-[50%]" : "left-[0%] mx-1.5")} 
          style={{ width: isAnnual ? 'calc(50% - 6px)' : 'calc(50% - 15px)' }}
        />
      </div>

      {/* Cards container */}
      <div className="w-full max-w-5xl grid md:grid-cols-2 gap-8 px-4 mb-24 justify-items-center">
        
        {/* Free Plan */}
        <div className="w-full max-w-md p-8 rounded-2xl bg-[#111827] border border-[#1E2D45] flex flex-col">
          <h2 className="text-2xl font-bold text-white mb-2">Free Forever</h2>
          <div className="flex items-end gap-1 mb-8">
            <span className="text-5xl font-bold font-mono text-white">₹0</span>
            <span className="text-text-secondary font-medium pb-1.5">/month</span>
          </div>
          
          <div className="flex-1 space-y-4 mb-8">
             <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500 shrink-0" /> <span className="text-white text-sm">Risk Assessment</span></div>
             <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500 shrink-0" /> <span className="text-white text-sm">Portfolio Analysis</span></div>
             <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500 shrink-0" /> <span className="text-white text-sm">Basic Rebalancing</span></div>
             <div className="flex items-center gap-3 opacity-40"><X className="w-5 h-5 text-text-muted shrink-0" /> <span className="text-text-muted text-sm">Crash Simulation</span></div>
             <div className="flex items-center gap-3 opacity-40"><X className="w-5 h-5 text-text-muted shrink-0" /> <span className="text-text-muted text-sm">Algo Trading</span></div>
          </div>

          <div className="flex flex-col items-center">
            <span className="px-4 py-1 rounded-full bg-slate-800 text-text-secondary text-xs font-bold uppercase tracking-widest mb-4">Your Current Plan</span>
            <button disabled className="w-full py-4 rounded-xl border border-[#1E2D45] bg-slate-800 text-text-muted font-bold cursor-not-allowed">
              Current Plan
            </button>
          </div>
        </div>

        {/* Pro Plan */}
        <div className="w-full max-w-md p-8 rounded-2xl bg-[#090E1A] border-2 border-transparent bg-clip-padding relative flex flex-col transform scale-105 shadow-[0_0_50px_rgba(59,130,246,0.1)] group">
          <div className="absolute inset-0 rounded-2xl border-2 border-transparent [background:linear-gradient(to_right,#3B82F6,#10B981)_border-box] [-webkit-mask:linear-gradient(#fff_0_0)_padding-box,linear-gradient(#fff_0_0)] [-webkit-mask-composite:destination-out] mask-composite-exclude" />
          
          <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1.5 bg-blue-600 text-white text-xs font-bold tracking-widest uppercase rounded-full shadow-[0_0_15px_rgba(59,130,246,0.5)]">
             Most Popular
          </div>

          <div className="flex items-center gap-2 mb-2">
            <h2 className="text-2xl font-bold text-white">Pro</h2>
            <Star className="w-5 h-5 text-gold-accent fill-gold-accent" />
          </div>
          
          <div className="flex items-end gap-1 mb-8">
            <span className="text-5xl font-bold font-mono text-white">₹{isAnnual ? '199' : '299'}</span>
            <span className="text-text-secondary font-medium pb-1.5">/month</span>
          </div>
          
          <div className="flex-1 space-y-4 mb-8">
             <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500 shrink-0" /> <span className="text-white text-sm font-medium">Risk Assessment</span></div>
             <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500 shrink-0" /> <span className="text-white text-sm font-medium">Portfolio Analysis</span></div>
             <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500 shrink-0" /> <span className="text-white text-sm font-medium">Crash Simulation</span></div>
             <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500 shrink-0" /> <span className="text-white text-sm font-medium">Algo Trading Sandbox</span></div>
             <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500 shrink-0" /> <span className="text-white text-sm font-medium">AI Voice Advisory</span></div>
             <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500 shrink-0" /> <span className="text-white text-sm font-medium">PDF Monthly Reports</span></div>
          </div>

          <div className="flex flex-col items-center">
            <button 
              onClick={() => setShowModal(true)}
              className="w-full py-4 rounded-xl bg-gradient-to-r from-blue-600 to-emerald-500 text-white font-bold text-lg relative overflow-hidden group/btn hover:shadow-[0_0_30px_rgba(16,185,129,0.3)] transition-all"
            >
              <div className="absolute inset-0 bg-white/20 -translate-x-full group-hover/btn:animate-[shimmer_1.5s_infinite]" />
              Upgrade Now
            </button>
            <p className="text-xs text-text-muted mt-4">Cancel anytime. No questions asked.</p>
          </div>
        </div>

      </div>

      {/* Feature Comparison Table */}
      <div className="w-full max-w-4xl px-4">
        <h3 className="text-2xl font-bold text-white text-center mb-8">Compare All Features</h3>
        <div className="rounded-2xl bg-slate-800 border border-border-subtle overflow-hidden">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-[#111827] border-b border-border-subtle">
              <tr>
                <th className="px-6 py-4 font-bold text-text-secondary uppercase tracking-wider">Features</th>
                <th className="px-6 py-4 font-bold text-white text-center">Free</th>
                <th className="px-6 py-4 font-bold text-blue-400 text-center relative overflow-hidden">
                  <div className="absolute inset-x-0 bottom-0 h-0.5 bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
                  Pro
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              {features.map((feat, i) => (
                <tr key={feat.name} className={cn("transition-colors", i % 2 === 0 ? "bg-slate-800" : "bg-slate-800/60")}>
                  <td className="px-6 py-4 font-medium text-white">{feat.name}</td>
                  <td className="px-6 py-4 text-center">
                    {feat.free ? <Check className="w-5 h-5 text-emerald-500 mx-auto" /> : <X className="w-5 h-5 text-text-muted mx-auto" />}
                  </td>
                  <td className="px-6 py-4 text-center">
                    {feat.pro ? <Check className="w-5 h-5 text-emerald-500 mx-auto" /> : <X className="w-5 h-5 text-text-muted mx-auto" />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
