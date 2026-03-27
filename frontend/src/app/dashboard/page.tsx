import { Bell, ArrowUpRight, ArrowDownRight, Activity, Calendar, ChevronDown, AlertTriangle } from "lucide-react";
import { PortfolioDonut } from "@/components/dashboard/PortfolioDonut";

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-8 pb-20 md:pb-8 animate-in fade-in duration-500">
      {/* Top Greeting Bar */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
          Good evening, Arjun 👋
        </h1>
        <div className="flex items-center gap-4">
          <button className="hidden sm:inline-flex px-4 py-2 rounded-full bg-warning-accent/10 border border-warning-accent/20 text-warning-accent text-sm font-semibold hover:bg-warning-accent/20 transition-colors shadow-[0_0_10px_rgba(245,158,11,0.15)]">
            Upgrade to Pro
          </button>
          <button className="relative p-2 rounded-full bg-slate-800 border border-border-subtle text-text-secondary hover:text-white transition-colors">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-danger-accent animate-pulse" />
          </button>
          <div className="w-10 h-10 rounded-full bg-slate-700 border border-border-subtle flex items-center justify-center text-white font-medium">
            AR
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle flex flex-col justify-between hover:-translate-y-1 transition-transform">
          <span className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">Portfolio Value</span>
          <div>
            <div className="text-2xl md:text-3xl font-bold font-mono text-white mb-1">₹4,83,200</div>
            <div className="flex items-center gap-1 text-emerald-accent text-sm font-medium">
              <ArrowUpRight className="w-4 h-4" /> +₹12,400 (+2.6%)
            </div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle flex flex-col justify-between hover:-translate-y-1 transition-transform">
          <span className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">Risk Score</span>
          <div>
            <div className="text-2xl md:text-3xl font-bold font-mono text-warning-accent mb-1 flex items-end gap-1">
              67<span className="text-sm text-text-muted pb-1">/100</span>
            </div>
            <div className="text-sm font-medium text-warning-accent">Moderate-Aggressive</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle flex flex-col justify-between hover:-translate-y-1 transition-transform">
          <span className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">Drift Status</span>
          <div>
            <div className="text-xl md:text-2xl font-bold text-warning-accent mb-1 flex items-center gap-2">
              <Activity className="w-5 h-5" /> 2 alerts
            </div>
            <div className="text-sm text-text-muted">Threshold breached</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle flex flex-col justify-between hover:-translate-y-1 transition-transform">
          <span className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2">Last Rebalance</span>
          <div>
            <div className="text-xl md:text-2xl font-bold text-white mb-1 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-500" /> 14 days
            </div>
            <div className="text-sm text-text-muted">Next review in 16d</div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main 2-cols: Portfolio Composition */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="grid md:grid-cols-2 gap-6 p-6 rounded-2xl bg-slate-800 border border-border-subtle">
            <div className="flex flex-col">
              <h2 className="text-lg font-bold text-white mb-6">Current Allocation</h2>
              <PortfolioDonut />
            </div>
            
            <div className="flex flex-col">
              <h2 className="text-lg font-bold text-white mb-6">Target vs Actual</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm mb-6">
                  <thead>
                    <tr className="border-b border-border-subtle text-text-muted">
                      <th className="pb-2 font-medium">Asset Class</th>
                      <th className="pb-2 font-medium text-right">Target</th>
                      <th className="pb-2 font-medium text-right">Actual</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle/50">
                    <tr>
                      <td className="py-3 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-blue-500" /> Equity</td>
                      <td className="py-3 text-right text-text-secondary font-mono">60%</td>
                      <td className="py-3 text-right font-mono text-warning-accent font-medium">62%</td>
                    </tr>
                    <tr>
                      <td className="py-3 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-emerald-500" /> Debt</td>
                      <td className="py-3 text-right text-text-secondary font-mono">20%</td>
                      <td className="py-3 text-right font-mono text-danger-accent font-medium">18%</td>
                    </tr>
                    <tr>
                      <td className="py-3 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-gold-accent" /> Gold</td>
                      <td className="py-3 text-right text-text-secondary font-mono">12%</td>
                      <td className="py-3 text-right font-mono text-emerald-accent font-medium">12%</td>
                    </tr>
                    <tr>
                      <td className="py-3 flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-slate-500" /> Cash</td>
                      <td className="py-3 text-right text-text-secondary font-mono">8%</td>
                      <td className="py-3 text-right font-mono text-emerald-accent font-medium">8%</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="p-4 rounded-xl border border-blue-500/30 bg-blue-600/10 mt-auto">
                <h3 className="text-sm font-bold text-white mb-1">Rebalance Needed</h3>
                <p className="text-xs text-text-secondary mb-3">₹8,200 equity → debt</p>
                <button className="w-full py-2 rounded flex items-center justify-center bg-blue-600 hover:bg-blue-500 transition-colors text-white text-sm font-medium">
                  View Details
                </button>
              </div>
            </div>
          </div>

          {/* Holdings Table */}
          <div className="rounded-2xl bg-slate-800 border border-border-subtle overflow-hidden">
            <div className="p-6 border-b border-border-subtle pb-4">
              <h2 className="text-lg font-bold text-white">Current Holdings</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-slate-800 border-b border-border-subtle text-text-muted">
                  <tr>
                    <th className="px-6 py-3 font-medium cursor-pointer hover:text-white transition-colors">
                      <div className="flex items-center gap-1">Stock/Fund <ChevronDown className="w-4 h-4" /></div>
                    </th>
                    <th className="px-6 py-3 font-medium">Asset Class</th>
                    <th className="px-6 py-3 font-medium text-right">Value (₹)</th>
                    <th className="px-6 py-3 font-medium text-right">Gain/Loss</th>
                    <th className="px-6 py-3 font-medium text-right">Weight %</th>
                    <th className="px-6 py-3 font-medium">Risk Flag</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  <tr className="bg-[#111827] hover:bg-slate-800/80 transition-colors">
                    <td className="px-6 py-4 font-medium text-white">RELIANCE</td>
                    <td className="px-6 py-4"><span className="px-2 py-1 rounded-md bg-blue-500/10 text-blue-400 text-xs border border-blue-500/20">Equity</span></td>
                    <td className="px-6 py-4 text-right font-mono">1,42,000</td>
                    <td className="px-6 py-4 text-right text-emerald-accent font-medium">+12.4%</td>
                    <td className="px-6 py-4 text-right font-mono">29.3%</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-warning-accent/10 border border-warning-accent/30 text-warning-accent text-xs font-medium">
                        <div className="w-1.5 h-1.5 rounded-full bg-warning-accent" /> High Concentration
                      </span>
                    </td>
                  </tr>
                  <tr className="bg-[#0F1623] hover:bg-slate-800/80 transition-colors">
                    <td className="px-6 py-4 font-medium text-white">HDFCBANK</td>
                    <td className="px-6 py-4"><span className="px-2 py-1 rounded-md bg-blue-500/10 text-blue-400 text-xs border border-blue-500/20">Equity</span></td>
                    <td className="px-6 py-4 text-right font-mono">85,200</td>
                    <td className="px-6 py-4 text-right text-danger-accent font-medium">-3.2%</td>
                    <td className="px-6 py-4 text-right font-mono">17.6%</td>
                    <td className="px-6 py-4">
                       <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-orange-500/10 border border-orange-500/30 text-orange-400 text-xs font-medium">
                        <div className="w-1.5 h-1.5 rounded-full bg-orange-500" /> Correlated
                      </span>
                    </td>
                  </tr>
                  <tr className="bg-[#111827] hover:bg-slate-800/80 transition-colors">
                    <td className="px-6 py-4 font-medium text-white">LIQUIDBEES</td>
                    <td className="px-6 py-4"><span className="px-2 py-1 rounded-md bg-slate-500/10 text-slate-400 text-xs border border-slate-500/20">Cash</span></td>
                    <td className="px-6 py-4 text-right font-mono">38,200</td>
                    <td className="px-6 py-4 text-right text-text-secondary font-medium">+0.0%</td>
                    <td className="px-6 py-4 text-right font-mono">7.9%</td>
                    <td className="px-6 py-4"></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="p-4 border-t border-border-subtle bg-slate-800/50 flex justify-center">
              <button className="text-sm font-medium text-blue-400 hover:text-blue-300">View All Holdings</button>
            </div>
          </div>
        </div>

        {/* Alerts Sidebar Card */}
        <div className="lg:col-span-1">
          <div className="rounded-2xl bg-slate-800 border border-border-subtle p-6 sticky top-24">
            <h2 className="text-lg font-bold text-white mb-6 flex items-center justify-between">
              Alerts & Recommendations
              <span className="px-2 py-0.5 rounded-full bg-blue-600 text-white text-xs font-bold">3</span>
            </h2>
            
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-slate-700/30 border border-border-subtle hover:border-warning-accent/50 transition-colors group">
                <div className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-warning-accent mt-1.5 shrink-0" />
                  <div>
                    <h3 className="text-sm font-bold text-white mb-1 group-hover:text-warning-accent transition-colors">Equity overweight</h3>
                    <p className="text-xs text-text-secondary mb-2">Equity weight 2% above target. Consider trimming reliance ahead of earnings.</p>
                    <span className="text-[10px] text-text-muted">Today, 09:41 AM</span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-700/30 border border-border-subtle hover:border-danger-accent/50 transition-colors group">
                <div className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-danger-accent mt-1.5 shrink-0" />
                  <div>
                    <h3 className="text-sm font-bold text-white mb-1 group-hover:text-danger-accent transition-colors">High Concentration</h3>
                    <p className="text-xs text-text-secondary mb-2">RELIANCE is 29.3% of your portfolio. Target max is 20%.</p>
                    <span className="text-[10px] text-text-muted">Yesterday</span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-700/30 border border-border-subtle hover:border-blue-500/50 transition-colors group">
                <div className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                  <div>
                    <h3 className="text-sm font-bold text-white mb-1 group-hover:text-blue-400 transition-colors">Tax Harvesting Alert</h3>
                    <p className="text-xs text-text-secondary mb-2">You can harvest ₹15,400 in short-term losses from HDFCBANK.</p>
                    <span className="text-[10px] text-text-muted">3 days ago</span>
                  </div>
                </div>
              </div>
            </div>
            
            <button className="w-full mt-6 py-3 rounded-xl border border-border-subtle text-text-secondary font-medium hover:bg-slate-700 hover:text-white transition-colors">
              Dismiss All
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
