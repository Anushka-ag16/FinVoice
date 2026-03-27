"use client";

import { useState } from "react";
import { Shield, Scale, Rocket, ChevronDown, Sparkles, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiAllocateInvestment } from "@/lib/api";

export default function NewInvestmentPage() {
  const [amount, setAmount] = useState("1,00,000");
  const [horizon, setHorizon] = useState("3Y");
  const [priority, setPriority] = useState("Growth");
  const [loss, setLoss] = useState(15);
  
  const [planGenerated, setPlanGenerated] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState("Balanced");
  const [isExplanationOpen, setIsExplanationOpen] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [apiData, setApiData] = useState<any>(null);

  const formatAmount = (val: string) => {
    const raw = val.replace(/\D/g, "");
    if (!raw) return "";
    return parseInt(raw).toLocaleString('en-IN');
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const payload = {
        amount: parseFloat(amount.replace(/,/g, "")) || 100000,
        goal: priority.toLowerCase(),
        horizon_years: parseInt(horizon.replace("Y", "")) || 3,
        max_acceptable_loss_pct: loss
      };
      const result = await apiAllocateInvestment(payload);
      setApiData(result);
      setPlanGenerated(true);
    } catch (err) {
      console.error(err);
      alert("Failed to generate plan.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 lg:flex-row pb-20 md:pb-8 animate-in fade-in duration-500">
      
      {/* Left Panel - Input Form */}
      <div className="w-full lg:w-1/3">
        <div className="p-6 rounded-2xl bg-slate-800 border border-border-subtle sticky top-24">
          <h2 className="text-sm font-bold text-text-muted uppercase tracking-wider mb-6">Investment Parameters</h2>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-white mb-2">How much do you want to invest?</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-text-secondary font-mono text-xl">₹</span>
                <input 
                  type="text" 
                  value={amount}
                  onChange={(e) => setAmount(formatAmount(e.target.value))}
                  className="w-full pl-10 pr-4 py-4 rounded-xl bg-[#111827] border border-[#1E2D45] text-white font-mono text-xl focus:border-blue-500 focus:outline-none transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-white mb-2">Investment Horizon</label>
              <div className="flex gap-2">
                {["1Y", "3Y", "5Y", "10Y", "20Y"].map(h => (
                  <button 
                    key={h}
                    onClick={() => setHorizon(h)}
                    className={cn(
                      "flex-1 py-2 rounded-lg border text-sm font-medium transition-colors",
                      horizon === h ? "bg-blue-600 border-blue-500 text-white" : "bg-[#111827] border-[#1E2D45] text-text-secondary hover:text-white"
                    )}
                  >
                    {h}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-white mb-2">Your Priority</label>
              <div className="space-y-2">
                {["Growth", "Income", "Capital Preservation"].map(p => (
                  <button 
                    key={p}
                    onClick={() => setPriority(p)}
                    className={cn(
                      "w-full px-4 py-3 rounded-xl border text-left text-sm font-medium transition-colors flex items-center justify-between",
                      priority === p ? "bg-blue-600/10 border-blue-500 text-white" : "bg-[#111827] border-[#1E2D45] text-text-secondary hover:text-white"
                    )}
                  >
                    {p}
                    {priority === p && <Sparkles className="w-4 h-4 text-blue-500" />}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <label className="font-medium text-white">Max Acceptable Loss</label>
                <span className="text-blue-400 font-mono">{loss}%</span>
              </div>
              <input 
                type="range" 
                min="5" max="50" step="1"
                value={loss}
                onChange={(e) => setLoss(parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <div className="flex justify-between text-[10px] text-text-muted mt-2 font-mono">
                <span>5%</span><span>50%</span>
              </div>
            </div>

            <button 
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full py-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold transition-all shadow-[0_0_20px_rgba(59,130,246,0.2)] hover:shadow-[0_0_30px_rgba(59,130,246,0.3)] mt-4 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isGenerating ? <><Activity className="w-5 h-5 animate-spin" /> Generating...</> : "Generate Plan"}
            </button>
          </div>
        </div>
      </div>

      {/* Right Panel - Scenario Cards */}
      <div className="w-full lg:w-2/3 flex flex-col gap-6">
        {!planGenerated ? (
          <div className="h-full min-h-[400px] flex flex-col items-center justify-center rounded-2xl border border-dashed border-border-subtle text-text-muted">
            <Sparkles className="w-8 h-8 mb-4 opacity-50" />
            <p>Set your parameters and generate an AI-optimized plan</p>
          </div>
        ) : (
          <>
            <div className="grid md:grid-cols-3 gap-4">
              {/* Conservative */}
              <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle flex flex-col transition-all">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-accent">
                    <Shield className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Safe Harbor</span>
                </div>
                <h3 className="text-lg font-bold text-white mb-1">Conservative</h3>
                <p className="text-xs text-text-secondary leading-relaxed mb-6 h-8">Preserve capital with steady yields.</p>
                
                {/* Mini Donut Placeholder */}
                <div className="w-20 h-20 rounded-full border-4 border-slate-700 mx-auto mb-6 relative">
                  <div className="absolute inset-0 rounded-full border-4 border-emerald-500" style={{ clipPath: 'polygon(0 0, 100% 0, 100% 100%, 0 100%, 0 0)', transform: 'rotate(25deg)' }} />
                  <div className="absolute inset-0 rounded-full border-4 border-gold-accent" style={{ clipPath: 'polygon(50% 50%, 100% 0, 100% 50%)' }} />
                </div>

                <div className="space-y-2 text-xs font-mono mb-6 flex-1">
                  <div className="flex justify-between"><span className="text-text-secondary">Bonds</span><span className="text-white">70% <span className="text-text-muted">₹70K</span></span></div>
                  <div className="flex justify-between"><span className="text-text-secondary">Gold</span><span className="text-white">20% <span className="text-text-muted">₹20K</span></span></div>
                  <div className="flex justify-between"><span className="text-text-secondary">Equity</span><span className="text-white">10% <span className="text-text-muted">₹10K</span></span></div>
                </div>

                <div className="p-3 rounded-xl bg-slate-900 mb-4 border border-border-subtle">
                  <div className="text-[10px] text-text-muted uppercase font-bold tracking-widest mb-1.5 flex justify-between">
                    <span>Projected Returns</span>
                  </div>
                  <div className="flex justify-between tracking-tight">
                    <span className="text-emerald-accent font-medium text-sm">₹1.06L</span>
                    <span className="text-text-secondary text-sm">max -4%</span>
                  </div>
                </div>

                <button 
                  onClick={() => setSelectedPlan("Conservative")}
                  className={cn("w-full py-2.5 rounded-xl font-medium text-sm transition-colors", selectedPlan === "Conservative" ? "bg-emerald-600 text-white" : "border border-emerald-500 text-emerald-400 hover:bg-emerald-500/10")}
                >
                  {selectedPlan === "Conservative" ? "Selected" : "Select Plan"}
                </button>
              </div>

              {/* Balanced */}
              <div className="p-5 rounded-2xl bg-slate-800 border-2 border-blue-500 relative flex flex-col shadow-[0_0_20px_rgba(59,130,246,0.15)] transform scale-105 z-10 transition-all">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-blue-600 text-white text-[10px] font-bold tracking-widest uppercase rounded-full shadow-lg">
                  Recommended
                </div>
                <div className="flex justify-between items-start mb-4 mt-2">
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
                    <Scale className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Golden Mean</span>
                </div>
                <h3 className="text-lg font-bold text-white mb-1">Balanced</h3>
                <p className="text-xs text-text-secondary leading-relaxed mb-6 h-8">Optimized risk-reward ratio.</p>

                <div className="w-20 h-20 rounded-full border-4 border-slate-700 mx-auto mb-6 relative">
                  <div className="absolute inset-0 rounded-full border-4 border-blue-500" style={{ clipPath: 'polygon(0 0, 100% 0, 100% 50%, 0 50%, 0 0)' }} />
                  <div className="absolute inset-0 rounded-full border-4 border-emerald-500" style={{ clipPath: 'polygon(50% 50%, 100% 50%, 100% 100%)' }} />
                  <div className="absolute inset-0 rounded-full border-4 border-slate-400" style={{ clipPath: 'polygon(0 50%, 50% 50%, 0 100%)' }} />
                </div>

                <div className="space-y-2 text-xs font-mono mb-6 flex-1">
                  <div className="flex justify-between"><span className="text-text-secondary">Equity</span><span className="text-white">55% <span className="text-text-muted">₹55K</span></span></div>
                  <div className="flex justify-between"><span className="text-text-secondary">Debt</span><span className="text-white">35% <span className="text-text-muted">₹35K</span></span></div>
                  <div className="flex justify-between"><span className="text-text-secondary">Cash</span><span className="text-white">10% <span className="text-text-muted">₹10K</span></span></div>
                </div>

                <div className="p-3 rounded-xl bg-[#090E1A] mb-4 border border-blue-500/30">
                  <div className="text-[10px] text-text-muted uppercase font-bold tracking-widest mb-1.5 flex justify-between">
                    <span>Projected Returns</span>
                  </div>
                  <div className="flex justify-between tracking-tight">
                    <span className="text-emerald-accent font-medium text-sm">₹1.18L</span>
                    <span className="text-text-secondary text-sm">max -11%</span>
                  </div>
                </div>

                <button 
                  onClick={() => setSelectedPlan("Balanced")}
                  className={cn("w-full py-2.5 rounded-xl font-medium text-sm transition-colors", selectedPlan === "Balanced" ? "bg-blue-600 text-white" : "bg-blue-600/20 text-blue-400 hover:bg-blue-600/30")}
                >
                  {selectedPlan === "Balanced" ? "Selected" : "Select Plan"}
                </button>
              </div>

              {/* Aggressive */}
              <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle flex flex-col transition-all">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
                    <Rocket className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Moonshot</span>
                </div>
                <h3 className="text-lg font-bold text-white mb-1">Aggressive</h3>
                <p className="text-xs text-text-secondary leading-relaxed mb-6 h-8">Maximum exposure for high growth.</p>

                <div className="w-20 h-20 rounded-full border-4 border-slate-700 mx-auto mb-6 relative">
                  <div className="absolute inset-0 rounded-full border-4 border-purple-500" style={{ clipPath: 'polygon(0 0, 100% 0, 100% 80%, 0 100%, 0 0)' }} />
                  <div className="absolute inset-0 rounded-full border-4 border-blue-500" style={{ clipPath: 'polygon(0 80%, 100% 80%, 100% 100%, 0 100%)' }} />
                </div>

                <div className="space-y-2 text-xs font-mono mb-6 flex-1">
                  <div className="flex justify-between"><span className="text-text-secondary">Sm. Cap</span><span className="text-white">40% <span className="text-text-muted">₹40K</span></span></div>
                  <div className="flex justify-between"><span className="text-text-secondary">Lg. Cap</span><span className="text-white">45% <span className="text-text-muted">₹45K</span></span></div>
                  <div className="flex justify-between"><span className="text-text-secondary">Crypto</span><span className="text-white">15% <span className="text-text-muted">₹15K</span></span></div>
                </div>

                <div className="p-3 rounded-xl bg-slate-900 mb-4 border border-border-subtle">
                  <div className="text-[10px] text-text-muted uppercase font-bold tracking-widest mb-1.5 flex justify-between">
                    <span>Projected Returns</span>
                  </div>
                  <div className="flex justify-between tracking-tight">
                    <span className="text-emerald-accent font-medium text-sm">₹1.32L</span>
                    <span className="text-danger-accent text-sm">max -28%</span>
                  </div>
                </div>

                <button 
                  onClick={() => setSelectedPlan("Aggressive")}
                  className={cn("w-full py-2.5 rounded-xl font-medium text-sm transition-colors", selectedPlan === "Aggressive" ? "bg-purple-600 text-white" : "border border-purple-500 text-purple-400 hover:bg-purple-500/10")}
                >
                  {selectedPlan === "Aggressive" ? "Selected" : "Select Plan"}
                </button>
              </div>
            </div>

            {/* Explanation Section */}
            <div className="mt-4 rounded-2xl bg-blue-900/10 border border-blue-500/30 overflow-hidden">
              <button 
                className="w-full flex items-center justify-between p-5 focus:outline-none"
                onClick={() => setIsExplanationOpen(!isExplanationOpen)}
              >
                <div className="flex items-center gap-3">
                  <Sparkles className="w-5 h-5 text-blue-400" />
                  <h3 className="font-bold text-white text-lg">Why this allocation?</h3>
                </div>
                <ChevronDown className={cn("w-5 h-5 text-text-secondary transition-transform", isExplanationOpen ? "rotate-180" : "rotate-0")} />
              </button>
              
              {isExplanationOpen && (
                <div className="p-5 pt-0 border-t border-border-subtle/50 animate-in slide-in-from-top-2 duration-300">
                  <p className="text-sm text-blue-100 leading-relaxed mb-6">
                    Based on your <strong className="text-white">3-year horizon</strong> and <strong className="text-white">15% loss tolerance</strong>, our AI model prioritized the <em className="text-white font-medium">Balanced Engine</em>. We've overweight Equity slightly due to favorable macro-indicators in the energy and tech sectors, while maintaining a Debt buffer to hedge against short-term volatility.
                  </p>
                  
                  <div className="border-t border-white/10 pt-4">
                    <h4 className="text-xs font-bold text-text-muted uppercase tracking-widest flex justify-between mb-4">
                      <span>Driving Factors (SHAP Analysis)</span>
                      <span>Live Impact Score</span>
                    </h4>
                    
                    <div className="space-y-3 font-mono text-xs">
                      <div className="flex items-center gap-4">
                        <span className="w-20 text-text-secondary">Horizon</span>
                        <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div className="w-3/4 h-full bg-blue-500 rounded-full" />
                        </div>
                        <span className="w-12 text-right text-blue-400 font-bold">+0.45</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="w-20 text-text-secondary">Loss Tol.</span>
                        <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div className="w-1/2 h-full bg-blue-400 rounded-full" />
                        </div>
                        <span className="w-12 text-right text-blue-400 font-bold">+0.30</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="w-20 text-text-secondary">Market Vol.</span>
                        <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden flex justify-end">
                          <div className="w-1/4 h-full bg-danger-accent rounded-full" />
                        </div>
                        <span className="w-12 text-right text-danger-accent font-bold">-0.15</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
