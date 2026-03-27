"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronRight, Brain, Activity, Shield, TrendingUp, Sunset, GraduationCap, X } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = ["Goals", "Behavior", "Knowledge", "Portfolio"];

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showResult, setShowResult] = useState(false);

  // Form State
  const [age, setAge] = useState(30);
  const [income, setIncome] = useState("< ₹25K");
  const [goal, setGoal] = useState("");
  const [horizon, setHorizon] = useState("");
  const [behavior, setBehavior] = useState("");
  const [experience, setExperience] = useState("");

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      setIsSubmitting(true);
      setTimeout(() => {
        setIsSubmitting(false);
        setShowResult(true);
      }, 1500);
    }
  };

  if (showResult) {
    return (
      <div className="min-h-screen bg-navy flex items-center justify-center p-4">
        <div className="w-full max-w-2xl bg-slate-800 rounded-2xl border border-border-subtle p-12 text-center animate-in fade-in zoom-in duration-500">
          <h2 className="text-3xl font-bold mb-8">Your Risk DNA</h2>
          
          <div className="relative w-48 h-48 mx-auto mb-8">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" stroke="#1E2D45" strokeWidth="8" fill="none" />
              <circle 
                cx="50" cy="50" r="40" 
                stroke="#EF4444" 
                strokeWidth="8" 
                fill="none" 
                strokeDasharray="251.2" 
                strokeDashoffset={251.2 * (1 - 67 / 100)} 
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-mono font-bold text-danger-accent">67</span>
              <span className="text-xs text-text-muted mt-1 uppercase tracking-widest">/ 100</span>
            </div>
          </div>
          <p className="text-xl font-medium text-danger-accent mb-8">Moderate-Aggressive</p>
          
          <div className="flex flex-wrap justify-center gap-3 mb-10">
            <span className="px-4 py-2 rounded-full bg-blue-600/20 text-blue-400 text-sm font-medium border border-blue-600/30">
              Intermediate Investor
            </span>
            <span className="px-4 py-2 rounded-full bg-purple-500/20 text-purple-400 text-sm font-medium border border-purple-500/30">
              Balanced Bias
            </span>
            <span className="px-4 py-2 rounded-full bg-emerald-500/20 text-emerald-400 text-sm font-medium border border-emerald-500/30">
              ₹50K – ₹10L Corpus
            </span>
          </div>
          
          <button 
            onClick={() => router.push("/dashboard")}
            className="w-full max-w-xs mx-auto py-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium transition-all shadow-[0_0_20px_rgba(59,130,246,0.2)] hover:shadow-[0_0_30px_rgba(59,130,246,0.4)]"
          >
            Go to Your Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-navy flex flex-col">
      {/* Top Progress Bar */}
      <div className="w-full bg-slate-800 border-b border-border-subtle p-4 md:px-12 sticky top-0 z-20">
        <div className="max-w-4xl mx-auto">
          <div className="flex justify-between mb-2">
            {STEPS.map((step, idx) => (
              <span key={step} className={cn(
                "text-xs md:text-sm font-bold uppercase tracking-wider transition-colors",
                idx <= currentStep ? "text-blue-500" : "text-text-muted"
              )}>
                {step}
              </span>
            ))}
          </div>
          <div className="w-full h-1 bg-slate-700 justify-end rounded-full overflow-hidden flex">
            <div 
              className="h-full bg-blue-600 rounded-full transition-all duration-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" 
              style={{ width: `${((currentStep) / (STEPS.length - 1)) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center p-4 md:p-8 relative overflow-hidden">
        <div className="w-full max-w-2xl relative">
          
          {/* STEP 1: GOALS */}
          {currentStep === 0 && (
            <div className="animate-in slide-in-from-right fade-in duration-500 space-y-10">
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-white">How old are you?</h3>
                <div className="relative pt-6">
                  <div className="absolute top-0 transform -translate-x-1/2 bg-blue-600 text-white font-mono text-sm px-2 py-1 rounded" style={{ left: `${((age - 18) / (80 - 18)) * 100}%` }}>
                    {age}
                  </div>
                  <input 
                    type="range" min="18" max="80" 
                    value={age} onChange={(e) => setAge(parseInt(e.target.value))}
                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                  <div className="flex justify-between text-xs text-text-muted mt-2">
                    <span>18</span><span>80</span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold text-white">What is your monthly income?</h3>
                <div className="grid grid-cols-2 gap-3">
                  {["< ₹25K", "₹25–75K", "₹75K–2L", "> ₹2L"].map((opt) => (
                    <button
                      key={opt}
                      onClick={() => setIncome(opt)}
                      className={cn(
                        "p-4 rounded-xl border text-center transition-all font-medium",
                        income === opt 
                          ? "border-blue-500 bg-blue-600/10 text-white shadow-[0_0_15px_rgba(59,130,246,0.15)]" 
                          : "border-border-subtle bg-slate-800 text-text-secondary hover:border-slate-500 hover:text-white"
                      )}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold text-white">Your primary investment goal?</h3>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { id: "growth", label: "Wealth Growth", icon: TrendingUp },
                    { id: "retirement", label: "Retirement", icon: Sunset },
                    { id: "education", label: "Education", icon: GraduationCap },
                    { id: "emergency", label: "Emergency Fund", icon: Shield },
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      onClick={() => setGoal(opt.id)}
                      className={cn(
                        "p-4 rounded-xl border flex flex-col items-center gap-3 transition-all",
                        goal === opt.id 
                          ? "border-blue-500 bg-blue-600/10 text-white shadow-[0_0_15px_rgba(59,130,246,0.15)]" 
                          : "border-border-subtle bg-slate-800 text-text-secondary hover:border-slate-500 hover:text-white"
                      )}
                    >
                      <opt.icon className={cn("w-6 h-6", goal === opt.id ? "text-blue-500" : "")} />
                      <span className="font-medium">{opt.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-xl font-bold text-white">Investment time horizon?</h3>
                <div className="flex flex-wrap gap-3">
                  {["1 yr", "3 yrs", "5 yrs", "10 yrs", "20+ yrs"].map((opt) => (
                    <button
                      key={opt}
                      onClick={() => setHorizon(opt)}
                      className={cn(
                        "px-6 py-3 rounded-full border transition-all font-medium",
                        horizon === opt 
                          ? "border-blue-500 bg-blue-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]" 
                          : "border-border-subtle bg-slate-800 text-text-secondary hover:border-slate-500 hover:text-white"
                      )}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: BEHAVIOR */}
          {currentStep === 1 && (
            <div className="animate-in slide-in-from-right fade-in duration-500 space-y-8">
              <div className="p-8 rounded-2xl bg-danger-accent/10 border border-danger-accent/30 text-center">
                <h2 className="text-2xl md:text-3xl font-bold text-white leading-tight">
                  If your portfolio dropped <span className="text-danger-accent">20%</span> tomorrow, you would...
                </h2>
              </div>
              <div className="space-y-3">
                {[
                  { id: "A", text: "Panic and sell everything" },
                  { id: "B", text: "Do nothing and wait" },
                  { id: "C", text: "Buy more at lower prices" },
                  { id: "D", text: "Analyze and partially rebalance" }
                ].map((opt) => (
                  <button
                    key={opt.id}
                    onClick={() => setBehavior(opt.id)}
                    className={cn(
                      "w-full p-6 flex items-center gap-4 rounded-xl border text-left transition-all",
                      behavior === opt.id 
                        ? "border-blue-500 bg-blue-600/10 shadow-[0_0_15px_rgba(59,130,246,0.15)]" 
                        : "border-border-subtle bg-slate-800 hover:border-slate-500"
                    )}
                  >
                    <div className={cn(
                      "w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0",
                      behavior === opt.id ? "border-blue-500" : "border-slate-500"
                    )}>
                      {behavior === opt.id && <div className="w-3 h-3 bg-blue-500 rounded-full" />}
                    </div>
                    <span className={cn("text-lg", behavior === opt.id ? "text-white font-medium" : "text-text-secondary")}>
                      {opt.text}
                    </span>
                  </button>
                ))}
              </div>
              {behavior && (
                <div className="h-1 bg-slate-800 w-full overflow-hidden rounded-full mt-8">
                  <div className="h-full w-1/3 bg-blue-500 rounded-full animate-[pulse_1.5s_ease-in-out_infinite]" />
                </div>
              )}
            </div>
          )}

          {/* STEP 3: KNOWLEDGE */}
          {currentStep === 2 && (
            <div className="animate-in slide-in-from-right fade-in duration-500 space-y-8">
               <div className="space-y-4">
                <h3 className="text-2xl font-bold text-white mb-6">Do you trade derivatives or use leverage?</h3>
                <div className="space-y-3">
                  {["No, only equity/MF", "Occasionally trade F&O", "Regular active trader"].map((opt) => (
                    <button
                      key={opt}
                      onClick={() => setExperience(opt)}
                      className={cn(
                        "w-full p-6 flex flex-col items-center justify-center rounded-xl border text-center transition-all",
                        experience === opt 
                          ? "border-blue-500 bg-blue-600/10 text-white shadow-[0_0_15px_rgba(59,130,246,0.15)]" 
                          : "border-border-subtle bg-slate-800 text-text-secondary hover:border-slate-500 hover:text-white"
                      )}
                    >
                      <span className="text-lg">{opt}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: PORTFOLIO */}
          {currentStep === 3 && (
            <div className="animate-in slide-in-from-right fade-in duration-500 space-y-8">
              <div className="text-center mb-10">
                <h2 className="text-3xl font-bold text-white mb-4">Import Your Holdings</h2>
                <p className="text-text-secondary">Optional: Enter a sample holding to generate your dashboard.</p>
              </div>
              
              <div className="bg-slate-800 rounded-xl border border-border-subtle p-6 overflow-hidden">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border-subtle">
                      <th className="pb-3 text-xs font-bold text-text-muted uppercase">Stock Ticker</th>
                      <th className="pb-3 text-xs font-bold text-text-muted uppercase">Quantity</th>
                      <th className="pb-3 text-xs font-bold text-text-muted uppercase">Buy Price (₹)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-border-subtle">
                      <td className="py-4"><input type="text" placeholder="e.g. RELIANCE" className="bg-transparent text-white font-mono uppercase focus:outline-none w-full" defaultValue="RELIANCE" /></td>
                      <td className="py-4"><input type="number" placeholder="0" className="bg-transparent text-white font-mono focus:outline-none w-full" defaultValue="45" /></td>
                      <td className="py-4"><input type="number" placeholder="0.00" className="bg-transparent text-white font-mono focus:outline-none w-full" defaultValue="2450.00" /></td>
                    </tr>
                    <tr>
                      <td className="py-4"><input type="text" placeholder="Add ticker" className="bg-transparent text-text-muted font-mono uppercase focus:outline-none w-full" /></td>
                      <td className="py-4"><input type="number" placeholder="0" className="bg-transparent text-text-muted font-mono focus:outline-none w-full" /></td>
                      <td className="py-4"><input type="number" placeholder="0.00" className="bg-transparent text-text-muted font-mono focus:outline-none w-full" /></td>
                    </tr>
                  </tbody>
                </table>
              </div>

            </div>
          )}

          {/* Form Actions */}
          <div className="mt-12 flex items-center justify-end gap-4 border-t border-border-subtle pt-6">
            <button 
              onClick={handleNext}
              disabled={isSubmitting}
              className="px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium w-full md:w-auto shadow-[0_0_15px_rgba(59,130,246,0.3)] flex items-center justify-center gap-2 transition-all disabled:opacity-70"
            >
              {isSubmitting ? (
                <>
                  <Activity className="w-5 h-5 animate-spin" /> Analyzing...
                </>
              ) : currentStep === STEPS.length - 1 ? (
                "Analyze My Portfolio" 
              ) : (
                <>Next Step <ChevronRight className="w-5 h-5" /></>
              )}
            </button>
          </div>
          
          {currentStep === 3 && (
            <div className="mt-4 text-center">
               <button onClick={handleNext} className="text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors">
                 Skip for now
               </button>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
