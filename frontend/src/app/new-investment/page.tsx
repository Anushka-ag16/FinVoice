"use client";

import { useState } from "react";
import { Shield, Scale, Rocket, ChevronDown, Sparkles, Activity, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFinStore } from "@/store/useFinStore";

type Allocation = {
  asset: string;
  pct: number;
  amount: string;
};

type Plan = {
  name: string;
  tagline: string;
  description: string;
  allocations: Allocation[];
  projected_return: string;
  max_drawdown: string;
  recommended: boolean;
  explanation: string;
};

type DrivingFactor = {
  factor: string;
  impact: number;
  direction: "positive" | "negative";
};

type InvestmentPlanData = {
  plans: Plan[];
  explanation_summary: string;
  driving_factors: DrivingFactor[];
};

const PLAN_STYLES: Record<string, { icon: typeof Shield; iconBg: string; iconColor: string; btnActive: string; btnInactive: string; badge: string }> = {
  Conservative: {
    icon: Shield,
    iconBg: "bg-emerald-100",
    iconColor: "text-emerald-600",
    btnActive: "bg-emerald-600 text-white",
    btnInactive: "border border-emerald-500 text-emerald-600 hover:bg-emerald-50",
    badge: "Safe Harbor",
  },
  Balanced: {
    icon: Scale,
    iconBg: "bg-blue-100",
    iconColor: "text-blue-600",
    btnActive: "bg-blue-600 text-white",
    btnInactive: "bg-blue-50 text-blue-600 hover:bg-blue-100",
    badge: "Golden Mean",
  },
  Aggressive: {
    icon: Rocket,
    iconBg: "bg-purple-100",
    iconColor: "text-purple-600",
    btnActive: "bg-purple-600 text-white",
    btnInactive: "border border-purple-500 text-purple-600 hover:bg-purple-50",
    badge: "Moonshot",
  },
};

export default function NewInvestmentPage() {
  const [amount, setAmount] = useState("1,00,000");
  const [horizon, setHorizon] = useState("3Y");
  const [priority, setPriority] = useState("Growth");
  const [loss, setLoss] = useState(15);
  
  const [planGenerated, setPlanGenerated] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [isExplanationOpen, setIsExplanationOpen] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [planData, setPlanData] = useState<InvestmentPlanData | null>(null);

  const riskProfile = useFinStore(s => s.riskProfile);

  const formatAmount = (val: string) => {
    const raw = val.replace(/\D/g, "");
    if (!raw) return "";
    return parseInt(raw).toLocaleString('en-IN');
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const numericAmount = parseFloat(amount.replace(/,/g, "")) || 100000;

      const res = await fetch("/api/investment-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount: numericAmount.toLocaleString('en-IN'),
          horizon,
          priority,
          loss,
          riskProfile: riskProfile ? {
            risk_level: riskProfile.risk_level,
            score: riskProfile.score,
            behavioral_bias: riskProfile.behavioral_bias,
            recommended_allocation: riskProfile.recommended_allocation,
          } : null,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `API error ${res.status}`);
      }

      const data: InvestmentPlanData = await res.json();
      setPlanData(data);
      
      // Auto-select the recommended plan
      const recommended = data.plans.find(p => p.recommended);
      setSelectedPlan(recommended?.name || data.plans[1]?.name || "Balanced");
      
      setPlanGenerated(true);
    } catch (err) {
      console.error("Failed to generate plan:", err);
      alert("Failed to generate plan. Please try again.");
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
          
          {riskProfile && (
            <div className="mb-6 p-3 rounded-xl bg-blue-50 border border-blue-200">
              <div className="flex items-center gap-2 mb-1">
                <Activity className="w-4 h-4 text-blue-600" />
                <span className="text-xs font-bold text-blue-700 uppercase tracking-wide">Risk Profile Linked</span>
              </div>
              <p className="text-xs text-slate-600">
                Score: <strong>{riskProfile.score}/100</strong> · Type: <strong className="capitalize">{riskProfile.risk_level}</strong>
                {riskProfile.behavioral_bias && <> · Bias: <strong className="capitalize">{riskProfile.behavioral_bias.replace('_', ' ')}</strong></>}
              </p>
            </div>
          )}

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
        {!planGenerated || !planData ? (
          <div className="h-full min-h-[400px] flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 text-slate-400">
            <Sparkles className="w-8 h-8 mb-4 opacity-50" />
            <p>Set your parameters and generate an AI-optimized plan</p>
          </div>
        ) : (
          <>
            <div className="grid md:grid-cols-3 gap-4">
              {planData.plans.map((plan) => {
                const style = PLAN_STYLES[plan.name] || PLAN_STYLES.Balanced;
                const IconComponent = style.icon;
                const isSelected = selectedPlan === plan.name;
                const isRecommended = plan.recommended;

                return (
                  <div 
                    key={plan.name}
                    className={cn(
                      "p-5 rounded-2xl bg-white flex flex-col transition-all",
                      isRecommended 
                        ? "border-2 border-blue-500 relative shadow-md transform scale-105 z-10" 
                        : "border border-slate-200 shadow-sm hover:-translate-y-1"
                    )}
                  >
                    {isRecommended && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-blue-600 text-white text-[10px] font-bold tracking-widest uppercase rounded-full shadow-lg">
                        Recommended
                      </div>
                    )}
                    <div className={cn("flex justify-between items-start mb-4", isRecommended && "mt-2")}>
                      <div className={cn("p-2 rounded-lg", style.iconBg, style.iconColor)}>
                        <IconComponent className="w-5 h-5" />
                      </div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        {plan.tagline || style.badge}
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-slate-900 mb-1">{plan.name}</h3>
                    <p className="text-xs text-slate-500 leading-relaxed mb-6 h-8">{plan.description}</p>

                    <div className="space-y-2 text-xs font-mono mb-6 flex-1">
                      {plan.allocations.map((alloc) => (
                        <div key={alloc.asset} className="flex justify-between">
                          <span className="text-slate-500">{alloc.asset}</span>
                          <span className="text-slate-900">
                            {alloc.pct}% <span className="text-slate-400">{alloc.amount}</span>
                          </span>
                        </div>
                      ))}
                    </div>

                    <div className={cn(
                      "p-3 rounded-xl mb-4 border",
                      isRecommended ? "bg-blue-50 border-blue-200" : "bg-slate-50 border-slate-200"
                    )}>
                      <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1.5">Projected Returns</div>
                      <div className="flex justify-between tracking-tight">
                        <span className="text-emerald-accent font-medium text-sm">{plan.projected_return}</span>
                        <span className={cn(
                          "text-sm",
                          plan.max_drawdown.includes("-") ? "text-danger-accent" : "text-slate-500"
                        )}>
                          max {plan.max_drawdown}
                        </span>
                      </div>
                    </div>

                    <button 
                      onClick={() => setSelectedPlan(plan.name)}
                      className={cn(
                        "w-full py-2.5 rounded-xl font-medium text-sm transition-colors",
                        isSelected ? style.btnActive : style.btnInactive
                      )}
                    >
                      {isSelected ? "Selected" : "Select Plan"}
                    </button>
                  </div>
                );
              })}
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
                    {planData.explanation_summary}
                  </p>
                  
                  {planData.driving_factors && planData.driving_factors.length > 0 && (
                    <div className="border-t border-blue-200 pt-4">
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex justify-between mb-4">
                        <span>Driving Factors (AI Analysis)</span>
                        <span>Impact Score</span>
                      </h4>
                      
                      <div className="space-y-3 font-mono text-xs">
                        {planData.driving_factors.map((factor) => (
                          <div key={factor.factor} className="flex items-center gap-4">
                            <span className="w-24 text-slate-500 flex items-center gap-1">
                              {factor.direction === "positive" 
                                ? <TrendingUp className="w-3 h-3 text-blue-500" /> 
                                : <TrendingDown className="w-3 h-3 text-red-500" />
                              }
                              {factor.factor}
                            </span>
                            <div className={cn(
                              "flex-1 h-2 bg-slate-200 rounded-full overflow-hidden",
                              factor.direction === "negative" && "flex justify-end"
                            )}>
                              <div 
                                className={cn(
                                  "h-full rounded-full",
                                  factor.direction === "positive" ? "bg-blue-500" : "bg-danger-accent"
                                )}
                                style={{ width: `${Math.abs(factor.impact) * 100}%` }}
                              />
                            </div>
                            <span className={cn(
                              "w-12 text-right font-bold",
                              factor.direction === "positive" ? "text-blue-600" : "text-danger-accent"
                            )}>
                              {factor.direction === "positive" ? "+" : "-"}{factor.impact.toFixed(2)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
