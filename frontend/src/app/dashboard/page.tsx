"use client";

import { useEffect, useState } from "react";
import { Bell, ArrowUpRight, ArrowDownRight, Activity, Calendar, ChevronDown, AlertTriangle } from "lucide-react";
import { PortfolioDonut } from "@/components/dashboard/PortfolioDonut";
import { apiAnalyzePortfolio, apiGetDrift, apiImportPortfolio } from "@/lib/api";
import { useFinStore } from "@/store/useFinStore";

export default function DashboardPage() {
  const user = useFinStore(state => state.user);
  const riskProfile = useFinStore(state => state.riskProfile);
  const { portfolioAnalysis, setPortfolioData } = useFinStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        let analysis: any;
        let driftData: any;
        
        try {
          analysis = await apiAnalyzePortfolio(1);
          driftData = await apiGetDrift(1);
        } catch (err: any) {
          if (err.message?.includes("Portfolio not found") || err.message?.includes("404")) {
            await apiImportPortfolio({
              portfolio_name: "Demo Portfolio",
              holdings: [
                { symbol: "RELIANCE", quantity: 45, buy_price: 2450.00 },
                { symbol: "HDFCBANK", quantity: 50, buy_price: 1500.00 },
                { symbol: "LIQUIDBEES", quantity: 38, buy_price: 1000.00 }
              ]
            });
            analysis = await apiAnalyzePortfolio(1);
            driftData = await apiGetDrift(1);
          } else {
            throw err;
          }
        }
        
        setPortfolioData([], analysis);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [setPortfolioData]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Activity className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 pb-20 md:pb-8 animate-in fade-in duration-500">
      {/* Top Greeting Bar */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">
          Good evening, {user?.first_name || "Investor"} 👋
        </h1>
        <div className="flex items-center gap-4">
          <button className="hidden sm:inline-flex px-4 py-2 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-sm font-semibold hover:bg-amber-100 transition-colors">
            Upgrade to Pro
          </button>
          <button className="relative p-2 rounded-full bg-white border border-slate-200 text-slate-500 hover:text-slate-900 hover:border-slate-300 transition-colors shadow-sm">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          </button>
          <div className="w-10 h-10 rounded-full bg-blue-600 border border-blue-700 flex items-center justify-center text-white font-medium uppercase text-sm">
            {user?.first_name?.charAt(0) || "U"}{user?.last_name?.charAt(0) || ""}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between hover:-translate-y-1 transition-transform shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Portfolio Value</span>
          <div>
            <div className="text-2xl md:text-3xl font-bold font-mono text-slate-900 mb-1">₹4,83,200</div>
            <div className="flex items-center gap-1 text-emerald-600 text-sm font-semibold">
              <ArrowUpRight className="w-4 h-4" /> +₹12,400 (+2.6%)
            </div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between hover:-translate-y-1 transition-transform shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Risk Score</span>
          <div>
            <div className="text-2xl md:text-3xl font-bold font-mono text-amber-600 mb-1 flex items-end gap-1">
              {riskProfile?.score || 67}<span className="text-sm text-slate-400 pb-1">/100</span>
            </div>
            <div className="text-sm font-semibold text-amber-600">{riskProfile?.risk_level || "Moderate"}</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between hover:-translate-y-1 transition-transform shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Drift Status</span>
          <div>
            <div className="text-xl md:text-2xl font-bold text-amber-600 mb-1 flex items-center gap-2">
              <Activity className="w-5 h-5" /> 2 alerts
            </div>
            <div className="text-sm text-slate-500">Threshold breached</div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-200 flex flex-col justify-between hover:-translate-y-1 transition-transform shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Last Rebalance</span>
          <div>
            <div className="text-xl md:text-2xl font-bold text-slate-900 mb-1 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-600" /> 14 days
            </div>
            <div className="text-sm text-slate-500">Next review in 16d</div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main 2-cols: Portfolio Composition */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="grid md:grid-cols-2 gap-6 p-6 rounded-2xl bg-white border border-slate-200 shadow-sm">
            <div className="flex flex-col">
              <h2 className="text-lg font-bold text-slate-900 mb-6">Current Allocation</h2>
              <PortfolioDonut />
            </div>
            
            <div className="flex flex-col">
              <h2 className="text-lg font-bold text-slate-900 mb-6">Target vs Actual</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm mb-6">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-400">
                      <th className="pb-2 font-medium">Asset Class</th>
                      <th className="pb-2 font-medium text-right">Target</th>
                      <th className="pb-2 font-medium text-right">Actual</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr>
                      <td className="py-3 flex items-center gap-2 text-slate-700"><div className="w-2 h-2 rounded-full bg-blue-500" /> Equity</td>
                      <td className="py-3 text-right text-slate-500 font-mono">60%</td>
                      <td className="py-3 text-right font-mono text-amber-600 font-semibold">62%</td>
                    </tr>
                    <tr>
                      <td className="py-3 flex items-center gap-2 text-slate-700"><div className="w-2 h-2 rounded-full bg-emerald-500" /> Debt</td>
                      <td className="py-3 text-right text-slate-500 font-mono">20%</td>
                      <td className="py-3 text-right font-mono text-red-600 font-semibold">18%</td>
                    </tr>
                    <tr>
                      <td className="py-3 flex items-center gap-2 text-slate-700"><div className="w-2 h-2 rounded-full bg-amber-500" /> Gold</td>
                      <td className="py-3 text-right text-slate-500 font-mono">12%</td>
                      <td className="py-3 text-right font-mono text-emerald-600 font-semibold">12%</td>
                    </tr>
                    <tr>
                      <td className="py-3 flex items-center gap-2 text-slate-700"><div className="w-2 h-2 rounded-full bg-slate-400" /> Cash</td>
                      <td className="py-3 text-right text-slate-500 font-mono">8%</td>
                      <td className="py-3 text-right font-mono text-emerald-600 font-semibold">8%</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="p-4 rounded-xl border border-blue-200 bg-blue-50 mt-auto">
                <h3 className="text-sm font-bold text-blue-900 mb-1">Rebalance Needed</h3>
                <p className="text-xs text-blue-700 mb-3">₹8,200 equity → debt</p>
                <button className="w-full py-2 rounded-lg flex items-center justify-center bg-blue-600 hover:bg-blue-700 transition-colors text-white text-sm font-semibold">
                  View Details
                </button>
              </div>
            </div>
          </div>

          {/* Holdings Table */}
          <div className="rounded-2xl bg-white border border-slate-200 overflow-hidden shadow-sm">
            <div className="p-6 border-b border-slate-200 pb-4">
              <h2 className="text-lg font-bold text-slate-900">Current Holdings</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-400">
                  <tr>
                    <th className="px-6 py-3 font-medium cursor-pointer hover:text-slate-700 transition-colors">
                      <div className="flex items-center gap-1">Stock/Fund <ChevronDown className="w-4 h-4" /></div>
                    </th>
                    <th className="px-6 py-3 font-medium">Asset Class</th>
                    <th className="px-6 py-3 font-medium text-right">Value (₹)</th>
                    <th className="px-6 py-3 font-medium text-right">Gain/Loss</th>
                    <th className="px-6 py-3 font-medium text-right">Weight %</th>
                    <th className="px-6 py-3 font-medium">Risk Flag</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="bg-white hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-900">RELIANCE</td>
                    <td className="px-6 py-4"><span className="px-2 py-1 rounded-md bg-blue-50 text-blue-700 text-xs border border-blue-200 font-medium">Equity</span></td>
                    <td className="px-6 py-4 text-right font-mono text-slate-700">1,42,000</td>
                    <td className="px-6 py-4 text-right text-emerald-600 font-semibold">+12.4%</td>
                    <td className="px-6 py-4 text-right font-mono text-slate-600">29.3%</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-xs font-semibold">
                        <div className="w-1.5 h-1.5 rounded-full bg-amber-500" /> High Concentration
                      </span>
                    </td>
                  </tr>
                  <tr className="bg-white hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-900">HDFCBANK</td>
                    <td className="px-6 py-4"><span className="px-2 py-1 rounded-md bg-blue-50 text-blue-700 text-xs border border-blue-200 font-medium">Equity</span></td>
                    <td className="px-6 py-4 text-right font-mono text-slate-700">85,200</td>
                    <td className="px-6 py-4 text-right text-red-600 font-semibold">-3.2%</td>
                    <td className="px-6 py-4 text-right font-mono text-slate-600">17.6%</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-orange-50 border border-orange-200 text-orange-700 text-xs font-semibold">
                        <div className="w-1.5 h-1.5 rounded-full bg-orange-500" /> Correlated
                      </span>
                    </td>
                  </tr>
                  <tr className="bg-white hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-900">LIQUIDBEES</td>
                    <td className="px-6 py-4"><span className="px-2 py-1 rounded-md bg-slate-100 text-slate-600 text-xs border border-slate-200 font-medium">Cash</span></td>
                    <td className="px-6 py-4 text-right font-mono text-slate-700">38,200</td>
                    <td className="px-6 py-4 text-right text-slate-500 font-semibold">+0.0%</td>
                    <td className="px-6 py-4 text-right font-mono text-slate-600">7.9%</td>
                    <td className="px-6 py-4"></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex justify-center">
              <button className="text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors">View All Holdings</button>
            </div>
          </div>
        </div>

        {/* Alerts Sidebar Card */}
        <div className="lg:col-span-1">
          <div className="rounded-2xl bg-white border border-slate-200 p-6 sticky top-24 shadow-sm">
            <h2 className="text-lg font-bold text-slate-900 mb-6 flex items-center justify-between">
              Alerts & Recommendations
              <span className="px-2 py-0.5 rounded-full bg-blue-600 text-white text-xs font-bold">3</span>
            </h2>
            
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 hover:border-amber-400 transition-colors group">
                <div className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 mb-1 group-hover:text-amber-700 transition-colors">Equity overweight</h3>
                    <p className="text-xs text-slate-600 mb-2">Equity weight 2% above target. Consider trimming reliance ahead of earnings.</p>
                    <span className="text-[10px] text-slate-400">Today, 09:41 AM</span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-red-50 border border-red-200 hover:border-red-400 transition-colors group">
                <div className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-red-500 mt-1.5 shrink-0" />
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 mb-1 group-hover:text-red-600 transition-colors">High Concentration</h3>
                    <p className="text-xs text-slate-600 mb-2">RELIANCE is 29.3% of your portfolio. Target max is 20%.</p>
                    <span className="text-[10px] text-slate-400">Yesterday</span>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 hover:border-blue-400 transition-colors group">
                <div className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 mb-1 group-hover:text-blue-600 transition-colors">Tax Harvesting Alert</h3>
                    <p className="text-xs text-slate-600 mb-2">You can harvest ₹15,400 in short-term losses from HDFCBANK.</p>
                    <span className="text-[10px] text-slate-400">3 days ago</span>
                  </div>
                </div>
              </div>
            </div>
            
            <button className="w-full mt-6 py-3 rounded-xl border border-slate-200 text-slate-600 font-semibold hover:bg-slate-50 hover:text-slate-900 transition-colors">
              Dismiss All
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
