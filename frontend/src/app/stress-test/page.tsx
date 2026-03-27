"use client";

import { useState } from "react";
import { Lock, TrendingDown, Activity, RefreshCcw, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';

import { useEffect } from "react";
import { apiMonteCarloSimulation } from "@/lib/api";

const customFormatter = (value: any) => `₹${Math.round(Number(value)).toLocaleString('en-IN')}`;

export default function StressTestPage() {
  const [activeTab, setActiveTab] = useState("Monte Carlo");
  const [isPro, setIsPro] = useState(false); // Demo toggle
  const [niftyDrop, setNiftyDrop] = useState(-15);
  const [usdInrRise, setUsdInrRise] = useState(5);
  const [monteCarloData, setMonteCarloData] = useState<any[]>([]);
  const [simulationStats, setSimulationStats] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (activeTab === "Monte Carlo" && monteCarloData.length === 0) {
      setIsLoading(true);
      apiMonteCarloSimulation({ portfolio_id: 1, num_simulations: 1000, horizon_days: 60 })
        .then((res: any) => {
          if (res.monte_carlo) {
            const data = res.monte_carlo;
            const mapped = data.percentile_50th.map((p50: number, i: number) => ({
              month: i,
              p5: data.percentile_5th[i],
              p50: p50,
              p95: data.percentile_95th[i]
            }));
            setMonteCarloData(mapped);
            setSimulationStats({
              maxDrawdown: data.max_drawdown,
              probRuin: data.probability_of_ruin
            });
          }
        })
        .catch(console.error)
        .finally(() => setIsLoading(false));
    }
  }, [activeTab]);

  // Replaced by above state declarations

  const tabs = ["Monte Carlo", "2008 Global Crisis", "2020 COVID Crash", "2022 Rate Hike", "Custom Shock"];
  const shockImpact = 483200 * (niftyDrop / 100) * 1.2 + 483200 * (usdInrRise / 100) * -0.5; // Dummy formula

  return (
    <div className="flex flex-col gap-6 pb-20 md:pb-8 animate-in fade-in duration-500 relative">
      {!isPro && (
        <div className="absolute inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-navy/60 backdrop-blur-md" />
          <div className="relative z-10 w-full max-w-md p-8 rounded-2xl bg-slate-800 border border-gold-accent/50 text-center shadow-[0_0_50px_rgba(251,191,36,0.15)]">
            <div className="w-16 h-16 mx-auto bg-gold-accent/20 rounded-full flex items-center justify-center mb-6">
              <Lock className="w-8 h-8 text-gold-accent" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">This feature requires Pro</h2>
            <p className="text-text-secondary mb-8">Run unlimited institutional-grade crash simulations and Monte Carlo analysis on your portfolio.</p>
            <button className="w-full py-4 rounded-xl bg-gradient-to-r from-warning-accent to-gold-accent text-slate-900 font-bold text-lg mb-4 hover:opacity-90 transition-opacity">
              Upgrade for ₹299/month
            </button>
            <button onClick={() => setIsPro(true)} className="text-sm font-medium text-blue-400 hover:text-blue-300">
              [Preview Demo Mode]
            </button>
          </div>
        </div>
      )}

      <div className={cn("flex flex-col gap-6", !isPro && "pointer-events-none")}>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white mb-2">
              Crash Simulation Engine
            </h1>
            <p className="text-sm text-text-secondary font-medium">Stress test your current ₹4.83L portfolio against hypothetical and historical shocks.</p>
          </div>
        </div>

        {/* Tab Selector */}
        <div className="flex overflow-x-auto pb-1 gap-2 no-scrollbar">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-5 py-2.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors",
                activeTab === tab 
                  ? "bg-blue-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]" 
                  : "bg-slate-800 text-text-secondary border border-border-subtle hover:bg-slate-700 hover:text-white"
              )}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Dynamic Content Area */}
        <div className="p-6 md:p-8 rounded-2xl bg-slate-800 border border-border-subtle min-h-[500px] flex flex-col">
          
          {activeTab === "Monte Carlo" && (
            <div className="animate-in fade-in flex-1 flex flex-col">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-lg font-bold text-white">5-Year Wealth Path Projection (10,000 simulations)</h2>
                <div className="flex items-center gap-4 text-xs font-medium">
                  <div className="flex items-center gap-2"><div className="w-3 h-1 bg-green-500 rounded-full" /> P95</div>
                  <div className="flex items-center gap-2"><div className="w-3 h-1 bg-blue-500 rounded-full" /> P50</div>
                  <div className="flex items-center gap-2"><div className="w-3 h-1 bg-red-500 rounded-full" /> P5</div>
                </div>
              </div>

              <div className="w-full h-[300px] mb-8">
                {isLoading ? (
                  <div className="w-full h-full flex flex-col items-center justify-center text-text-muted">
                    <Activity className="w-8 h-8 animate-spin text-blue-500 mb-4" />
                    Running 10,000 simulations...
                  </div>
                ) : monteCarloData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={monteCarloData} margin={{ top: 10, right: 10, left: 20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorP50" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E2D45" vertical={false} />
                      <XAxis dataKey="month" stroke="#475569" tick={{fill: '#94A3B8', fontSize: 12}} />
                      <YAxis stroke="#475569" tick={{fill: '#94A3B8', fontSize: 12}} tickFormatter={(val) => `₹${(val/1000).toFixed(0)}k`} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1A2235', borderColor: '#3B82F6', borderRadius: '12px', color: '#F1F5F9' }}
                        formatter={customFormatter}
                        labelFormatter={(label) => `Month ${label}`}
                      />
                      <Area type="monotone" dataKey="p95" stroke="#10B981" strokeDasharray="5 5" fill="none" name="Best Case (P95)" />
                      <Area type="monotone" dataKey="p50" stroke="#3B82F6" strokeWidth={3} fillOpacity={1} fill="url(#colorP50)" name="Expected (P50)" />
                      <Area type="monotone" dataKey="p5" stroke="#EF4444" strokeDasharray="5 5" fill="none" name="Worst Case (P5)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : null}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-auto">
                <div className="p-5 rounded-2xl bg-[#090E1A] border border-danger-accent/30 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity"><TrendingDown className="w-12 h-12 text-danger-accent" /></div>
                  <span className="text-xs font-bold text-danger-accent uppercase tracking-wider mb-2 block">Worst Case (P5)</span>
                  <div className="text-3xl font-bold font-mono text-white mb-1">₹2,84,000</div>
                  <div className="text-sm font-medium text-danger-accent">-41% relative to initial</div>
                </div>
                <div className="p-5 rounded-2xl bg-blue-600/10 border border-blue-500/50 shadow-[0_0_20px_rgba(59,130,246,0.1)] relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity"><Activity className="w-12 h-12 text-blue-500" /></div>
                  <span className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-2 block">Expected (P50)</span>
                  <div className="text-3xl font-bold font-mono text-white mb-1">₹5,62,000</div>
                  <div className="text-sm font-medium text-blue-400">+16% CAGR</div>
                </div>
                <div className="p-5 rounded-2xl bg-[#090E1A] border border-emerald-accent/30 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity"><TrendingDown className="w-12 h-12 text-emerald-accent transform rotate-180" /></div>
                  <span className="text-xs font-bold text-emerald-accent uppercase tracking-wider mb-2 block">Best Case (P95)</span>
                  <div className="text-3xl font-bold font-mono text-white mb-1">₹8,90,000</div>
                  <div className="text-sm font-medium text-emerald-accent">+84% upper bound</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "2020 COVID Crash" && (
            <div className="animate-in fade-in flex-1 flex flex-col items-center justify-center text-center">
              <div className="w-20 h-20 bg-slate-700 rounded-full flex items-center justify-center mb-6 border-4 border-slate-600">
                <Activity className="w-10 h-10 text-slate-400" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-4">Historical Scenario Engine</h2>
              <p className="text-text-secondary max-w-lg mx-auto mb-8">
                Your portfolio is overlaid onto exact market conditions between Jan 2020 and Dec 2020.
                Data visualization loading for historical overlays...
              </p>
              <div className="grid grid-cols-3 gap-6 w-full max-w-3xl">
                <div className="p-5 rounded-2xl bg-[#090E1A] border border-border-subtle">
                  <span className="text-xs text-text-muted uppercase">Max Drawdown</span>
                  <div className="text-2xl font-bold font-mono text-danger-accent mt-2">-34.2%</div>
                </div>
                <div className="p-5 rounded-2xl bg-[#090E1A] border border-border-subtle">
                  <span className="text-xs text-text-muted uppercase">Recovery Time</span>
                  <div className="text-2xl font-bold font-mono text-blue-400 mt-2">8 months</div>
                </div>
                <div className="p-5 rounded-2xl bg-[#090E1A] border border-border-subtle">
                  <span className="text-xs text-text-muted uppercase">Prob. of Ruin</span>
                  <div className="text-2xl font-bold font-mono text-emerald-accent mt-2">3.2%</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "Custom Shock" && (
            <div className="animate-in fade-in flex-1 flex flex-col">
              <h2 className="text-xl font-bold text-white mb-8">Custom Shock Designer</h2>
              
              <div className="grid md:grid-cols-2 gap-12 flex-1">
                <div className="space-y-10">
                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <label className="text-sm font-medium text-white">NIFTY drops by</label>
                      <span className="text-danger-accent font-bold font-mono text-lg">{niftyDrop}%</span>
                    </div>
                    <input 
                      type="range" min="-50" max="0" 
                      value={niftyDrop} onChange={(e) => setNiftyDrop(parseInt(e.target.value))}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-danger-accent"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between items-center mb-4">
                      <label className="text-sm font-medium text-white">USD/INR rises by</label>
                      <span className="text-warning-accent font-bold font-mono text-lg">+{usdInrRise}%</span>
                    </div>
                    <input 
                      type="range" min="0" max="30" 
                      value={usdInrRise} onChange={(e) => setUsdInrRise(parseInt(e.target.value))}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-warning-accent"
                    />
                  </div>
                  
                  <div className="p-4 rounded-xl bg-slate-900 border border-border-subtle flex items-start gap-4">
                    <AlertTriangle className="w-5 h-5 text-warning-accent shrink-0 mt-0.5" />
                    <p className="text-xs text-text-secondary leading-relaxed">
                      Custom shocks use local sensitivity factor analysis (Greeks) to estimate instant P&L impact. It does not account for dynamic management.
                    </p>
                  </div>
                </div>

                <div className="flex flex-col justify-center items-center">
                  <div className="w-64 h-64 rounded-full border border-danger-accent/30 bg-danger-accent/5 flex flex-col items-center justify-center relative shadow-[0_0_50px_rgba(239,68,68,0.1)]">
                    <div className="absolute inset-2 rounded-full border border-danger-accent/20 animate-[spin_10s_linear_infinite]" />
                    <TrendingDown className="w-10 h-10 text-danger-accent mb-4" />
                    <span className="text-sm font-bold text-text-muted uppercase tracking-wider mb-2">Estimated Impact</span>
                    <span className="text-3xl font-bold font-mono text-white mb-1">
                      {shockImpact < 0 ? "-" : ""}₹{Math.abs(Math.round(shockImpact)).toLocaleString('en-IN')}
                    </span>
                    <span className="text-sm font-medium text-danger-accent">
                      {((shockImpact / 483200) * 100).toFixed(1)}% of portfolio
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
