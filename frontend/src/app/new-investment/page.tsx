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
        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm sticky top-24">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-6">Investment Parameters</h2>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">How much do you want to invest?</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 font-mono text-xl">₹</span>
                <input 
                  type="text" 
                  value={amount}
                  onChange={(e) => setAmount(formatAmount(e.target.value))}
                  className="w-full pl-10 pr-4 py-4 rounded-xl bg-slate-50 border border-slate-200 text-slate-900 font-mono text-xl focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Investment Horizon</label>
              <div className="flex gap-2">
                {["1Y", "3Y", "5Y", "10Y", "20Y"].map(h => (
                  <button 
                    key={h}
                    onClick={() => setHorizon(h)}
                    className={cn(
                      "flex-1 py-2 rounded-lg border text-sm font-medium transition-colors",
                      horizon === h ? "bg-blue-600 border-blue-500 text-white" : "bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300"
                    )}
                  >
                    {h}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Your Priority</label>
              <div className="space-y-2">
                {["Growth", "Income", "Capital Preservation"].map(p => (
                  <button 
                    key={p}
                    onClick={() => setPriority(p)}
                    className={cn(
                      "w-full px-4 py-3 rounded-xl border text-left text-sm font-medium transition-colors flex items-center justify-between",
                      priority === p ? "bg-blue-50 border-blue-500 text-blue-700" : "bg-slate-50 border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300"
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
                <label className="font-medium text-slate-700">Max Acceptable Loss</label>
                <span className="text-blue-600 font-mono">{loss}%</span>
              </div>
              <input 
                type="range" 
                min="5" max="50" step="1"
                value={loss}
                onChange={(e) => setLoss(parseInt(e.target.value))}
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <div className="flex justify-between text-[10px] text-slate-400 mt-2 font-mono">
                <span>5%</span><span>50%</span>
              </div>
            </div>

            <button 
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full py-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold transition-all shadow-sm mt-4 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isGenerating ? <><Activity className="w-5 h-5 animate-spin" /> Generating...</> : "Generate Plan"}
            </button>
          </div>
        </div>
      </div>

      {/* Right Panel - Scenario Cards */}
      <div className="w-full lg:w-2/3 flex flex-col gap-6">
        {!planGenerated ? (
          <div className="h-full min-h-[400px] flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 text-slate-400">
            <Sparkles className="w-8 h-8 mb-4 opacity-50" />
            <p>Set your parameters and generate an AI-optimized plan</p>
          </div>
        ) : (
          <>
            <div className="grid md:grid-cols-3 gap-4">
              {/* Conservative */}
              <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col transition-all hover:-translate-y-1">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-2 rounded-lg bg-emerald-100 text-emerald-600">
                    <Shield className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Safe Harbor</span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">Conservative</h3>
                <p className="text-xs text-slate-500 leading-relaxed mb-6 h-8">Preserve capital with steady yields.</p>
                
                <div className="w-20 h-20 rounded-full border-4 border-slate-200 mx-auto mb-6 relative">
                  <div className="absolute inset-0 rounded-full border-4 border-emerald-500" style={{ clipPath: 'polygon(0 0, 100% 0, 100% 100%, 0 100%, 0 0)', transform: 'rotate(25deg)' }} />
                  <div className="absolute inset-0 rounded-full border-4 border-gold-accent" style={{ clipPath: 'polygon(50% 50%, 100% 0, 100% 50%)' }} />
                </div>

                <div className="space-y-2 text-xs font-mono mb-6 flex-1">
                  <div className="flex justify-between"><span className="text-slate-500">Bonds</span><span className="text-slate-900">70% <span className="text-slate-400">₹70K</span></span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Gold</span><span className="text-slate-900">20% <span className="text-slate-400">₹20K</span></span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Equity</span><span className="text-slate-900">10% <span className="text-slate-400">₹10K</span></span></div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 mb-4 border border-slate-200">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1.5">Projected Returns</div>
                  <div className="flex justify-between tracking-tight">
                    <span className="text-emerald-accent font-medium text-sm">₹1.06L</span>
                    <span className="text-slate-500 text-sm">max -4%</span>
                  </div>
                </div>

                <button 
                  onClick={() => setSelectedPlan("Conservative")}
                  className={cn("w-full py-2.5 rounded-xl font-medium text-sm transition-colors", selectedPlan === "Conservative" ? "bg-emerald-600 text-white" : "border border-emerald-500 text-emerald-600 hover:bg-emerald-50")}
                >
                  {selectedPlan === "Conservative" ? "Selected" : "Select Plan"}
                </button>
              </div>

              {/* Balanced */}
              <div className="p-5 rounded-2xl bg-white border-2 border-blue-500 relative flex flex-col shadow-md transform scale-105 z-10 transition-all">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-blue-600 text-white text-[10px] font-bold tracking-widest uppercase rounded-full shadow-lg">
                  Recommended
                </div>
                <div className="flex justify-between items-start mb-4 mt-2">
                  <div className="p-2 rounded-lg bg-blue-100 text-blue-600">
                    <Scale className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Golden Mean</span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">Balanced</h3>
                <p className="text-xs text-slate-500 leading-relaxed mb-6 h-8">Optimized risk-reward ratio.</p>

                <div className="w-20 h-20 rounded-full border-4 border-slate-200 mx-auto mb-6 relative">
                  <div className="absolute inset-0 rounded-full border-4 border-blue-500" style={{ clipPath: 'polygon(0 0, 100% 0, 100% 50%, 0 50%, 0 0)' }} />
                  <div className="absolute inset-0 rounded-full border-4 border-emerald-500" style={{ clipPath: 'polygon(50% 50%, 100% 50%, 100% 100%)' }} />
                  <div className="absolute inset-0 rounded-full border-4 border-slate-400" style={{ clipPath: 'polygon(0 50%, 50% 50%, 0 100%)' }} />
                </div>

                <div className="space-y-2 text-xs font-mono mb-6 flex-1">
                  <div className="flex justify-between"><span className="text-slate-500">Equity</span><span className="text-slate-900">55% <span className="text-slate-400">₹55K</span></span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Debt</span><span className="text-slate-900">35% <span className="text-slate-400">₹35K</span></span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Cash</span><span className="text-slate-900">10% <span className="text-slate-400">₹10K</span></span></div>
                </div>

                <div className="p-3 rounded-xl bg-blue-50 mb-4 border border-blue-200">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1.5">Projected Returns</div>
                  <div className="flex justify-between tracking-tight">
                    <span className="text-emerald-accent font-medium text-sm">₹1.18L</span>
                    <span className="text-slate-500 text-sm">max -11%</span>
                  </div>
                </div>

                <button 
                  onClick={() => setSelectedPlan("Balanced")}
                  className={cn("w-full py-2.5 rounded-xl font-medium text-sm transition-colors", selectedPlan === "Balanced" ? "bg-blue-600 text-white" : "bg-blue-50 text-blue-600 hover:bg-blue-100")}
                >
                  {selectedPlan === "Balanced" ? "Selected" : "Select Plan"}
                </button>
              </div>

              {/* Aggressive */}
              <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col transition-all hover:-translate-y-1">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-2 rounded-lg bg-purple-100 text-purple-600">
                    <Rocket className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Moonshot</span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">Aggressive</h3>
                <p className="text-xs text-slate-500 leading-relaxed mb-6 h-8">Maximum exposure for high growth.</p>

                <div className="w-20 h-20 rounded-full border-4 border-slate-200 mx-auto mb-6 relative">
                  <div className="absolute inset-0 rounded-full border-4 border-purple-500" style={{ clipPath: 'polygon(0 0, 100% 0, 100% 80%, 0 100%, 0 0)' }} />
                  <div className="absolute inset-0 rounded-full border-4 border-blue-500" style={{ clipPath: 'polygon(0 80%, 100% 80%, 100% 100%, 0 100%)' }} />
                </div>

                <div className="space-y-2 text-xs font-mono mb-6 flex-1">
                  <div className="flex justify-between"><span className="text-slate-500">Sm. Cap</span><span className="text-slate-900">40% <span className="text-slate-400">₹40K</span></span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Lg. Cap</span><span className="text-slate-900">45% <span className="text-slate-400">₹45K</span></span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Crypto</span><span className="text-slate-900">15% <span className="text-slate-400">₹15K</span></span></div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 mb-4 border border-slate-200">
                  <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1.5">Projected Returns</div>
                  <div className="flex justify-between tracking-tight">
                    <span className="text-emerald-accent font-medium text-sm">₹1.32L</span>
                    <span className="text-danger-accent text-sm">max -28%</span>
                  </div>
                </div>

                <button 
                  onClick={() => setSelectedPlan("Aggressive")}
                  className={cn("w-full py-2.5 rounded-xl font-medium text-sm transition-colors", selectedPlan === "Aggressive" ? "bg-purple-600 text-white" : "border border-purple-500 text-purple-600 hover:bg-purple-50")}
                >
                  {selectedPlan === "Aggressive" ? "Selected" : "Select Plan"}
                </button>
              </div>
            </div>

            {/* Explanation Section */}
            <div className="mt-4 rounded-2xl bg-blue-50 border border-blue-200 overflow-hidden">
              <button 
                className="w-full flex items-center justify-between p-5 focus:outline-none"
                onClick={() => setIsExplanationOpen(!isExplanationOpen)}
              >
                <div className="flex items-center gap-3">
                  <Sparkles className="w-5 h-5 text-blue-500" />
                  <h3 className="font-bold text-slate-900 text-lg">Why this allocation?</h3>
                </div>
                <ChevronDown className={cn("w-5 h-5 text-slate-400 transition-transform", isExplanationOpen ? "rotate-180" : "rotate-0")} />
              </button>
              
              {isExplanationOpen && (
                <div className="p-5 pt-0 border-t border-blue-200 animate-in slide-in-from-top-2 duration-300">
                  <p className="text-sm text-slate-700 leading-relaxed mb-6">
                    Based on your <strong className="text-slate-900">3-year horizon</strong> and <strong className="text-slate-900">15% loss tolerance</strong>, our AI model prioritized the <em className="text-blue-700 font-medium">Balanced Engine</em>. We've overweight Equity slightly due to favorable macro-indicators in the energy and tech sectors, while maintaining a Debt buffer to hedge against short-term volatility.
                  </p>
                  
                  <div className="border-t border-blue-200 pt-4">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex justify-between mb-4">
                      <span>Driving Factors (SHAP Analysis)</span>
                      <span>Live Impact Score</span>
                    </h4>
                    
                    <div className="space-y-3 font-mono text-xs">
                      <div className="flex items-center gap-4">
                        <span className="w-20 text-slate-500">Horizon</span>
                        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                          <div className="w-3/4 h-full bg-blue-500 rounded-full" />
                        </div>
                        <span className="w-12 text-right text-blue-600 font-bold">+0.45</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="w-20 text-slate-500">Loss Tol.</span>
                        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                          <div className="w-1/2 h-full bg-blue-400 rounded-full" />
                        </div>
                        <span className="w-12 text-right text-blue-600 font-bold">+0.30</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="w-20 text-slate-500">Market Vol.</span>
                        <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden flex justify-end">
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
