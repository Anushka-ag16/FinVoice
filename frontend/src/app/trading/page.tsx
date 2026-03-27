"use client";

import { useState } from "react";
import { Search, Trophy, TrendingUp, TrendingDown, Edit3, ArrowUpRight } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { cn } from "@/lib/utils";

const performanceData = Array.from({ length: 30 }).map((_, i) => ({
  day: i,
  portfolio: 1000000 + (Math.sin(i / 3) * 15000) + (i * 2000),
  benchmark: 1000000 + (Math.sin(i / 5) * 8000) + (i * 1200)
}));

export default function PaperTradingPage() {
  const [orderType, setOrderType] = useState("Market");
  const [tradeAction, setTradeAction] = useState("Buy");
  
  return (
    <div className="flex flex-col gap-6 pb-20 md:pb-8 animate-in fade-in duration-500">
      
      {/* Top Banner */}
      <div className="w-full bg-warning-accent/10 border border-warning-accent/30 rounded-xl p-3 flex flex-col sm:flex-row items-center justify-between gap-3 text-warning-accent font-medium text-sm">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-warning-accent animate-pulse" />
          <span>Paper Trading — Simulated with real NSE/BSE prices</span>
        </div>
        <div className="px-3 py-1 bg-warning-accent/20 rounded-full text-xs font-bold tracking-wider uppercase border border-warning-accent/30">
          ₹0 Real Money Involved
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        
        {/* Main Content (2/3) */}
        <div className="w-full lg:w-2/3 flex flex-col gap-6">
          
          {/* Portfolio Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-800 border border-border-subtle">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1 block">Virtual Wallet</span>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-white">₹9,74,200</span>
              </div>
              <div className="text-[10px] text-text-secondary mt-1">Started ₹10.0L</div>
            </div>
            
            <div className="p-4 rounded-xl bg-slate-800 border border-border-subtle">
               <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1 block">Unrealized P&L</span>
               <div className="text-xl font-bold font-mono text-emerald-accent">+₹23,400</div>
               <div className="text-[10px] text-emerald-accent mt-1">+2.4% Overall</div>
            </div>
            
            <div className="p-4 rounded-xl bg-slate-800 border border-border-subtle">
               <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1 block">Sharpe Ratio</span>
               <div className="text-xl font-bold font-mono text-white">0.73</div>
               <div className="text-[10px] text-blue-400 mt-1">Target &gt; 0.5</div>
            </div>
            
            <div className="p-4 rounded-xl bg-slate-800 border border-border-subtle">
               <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1 block">Days Active</span>
               <div className="text-xl font-bold font-mono text-white">14 / 30</div>
               <div className="text-[10px] text-text-secondary mt-1">To graduate</div>
            </div>
          </div>

          {/* Performance Chart */}
          <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle h-[300px] flex flex-col">
            <h2 className="text-sm font-bold text-white mb-4">Paper Performance vs NIFTY50</h2>
            <div className="flex-1 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={performanceData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPf" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" hide />
                  <YAxis domain={['dataMin - 10000', 'dataMax + 10000']} hide />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1A2235', borderColor: '#1E2D45', borderRadius: '8px', color: '#F1F5F9' }}
                    labelFormatter={() => ''}
                    formatter={(value: any) => [`₹${Math.round(Number(value)).toLocaleString('en-IN')}`]}
                  />
                  <Area type="monotone" dataKey="benchmark" stroke="#475569" strokeDasharray="5 5" fill="none" name="NIFTY50" />
                  <Area type="monotone" dataKey="portfolio" stroke="#10B981" strokeWidth={2} fillOpacity={1} fill="url(#colorPf)" name="Your Paper Pf" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Graduate Card (Demo) */}
          <div className="p-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex flex-col sm:flex-row items-center justify-between gap-6 relative overflow-hidden group">
            <div className="absolute inset-0 bg-emerald-500/5 -translate-x-full group-hover:animate-[shimmer_2s_infinite]" />
            <div className="flex items-center gap-4 z-10">
              <div className="w-14 h-14 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0 border border-emerald-500/30">
                <Trophy className="w-7 h-7 text-emerald-accent" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white mb-1">You've earned your Live Trading Badge!</h3>
                <p className="text-sm text-emerald-100">Your 30-day Sharpe: <strong className="text-white">0.91</strong>. You've consistently beaten the baseline.</p>
              </div>
            </div>
            <button className="w-full sm:w-auto px-6 py-3 shrink-0 rounded-xl bg-gradient-to-r from-orange-500 to-gold-accent text-slate-900 font-bold transition-transform hover:scale-105 shadow-[0_0_20px_rgba(245,158,11,0.3)] z-10">
              Go Live Now
            </button>
          </div>

          {/* Active Positions Table */}
          <div className="rounded-2xl bg-slate-800 border border-border-subtle overflow-hidden">
             <div className="p-5 border-b border-border-subtle">
               <h2 className="text-lg font-bold text-white">Active Paper Positions</h2>
             </div>
             <div className="overflow-x-auto">
               <table className="w-full text-left text-sm whitespace-nowrap">
                 <thead className="bg-[#111827] border-b border-border-subtle text-text-muted">
                   <tr>
                     <th className="px-5 py-3 font-medium">Ticker</th>
                     <th className="px-5 py-3 font-medium text-right">Qty</th>
                     <th className="px-5 py-3 font-medium text-right">Avg Price</th>
                     <th className="px-5 py-3 font-medium text-right">LTP</th>
                     <th className="px-5 py-3 font-medium text-right">P&L</th>
                     <th className="px-5 py-3 font-medium text-right">Stop Loss</th>
                     <th className="px-5 py-3 font-medium text-right">Actions</th>
                   </tr>
                 </thead>
                 <tbody className="divide-y divide-border-subtle">
                   <tr className="bg-slate-800 hover:bg-slate-700/50 transition-colors">
                     <td className="px-5 py-4 font-bold text-white">INFY</td>
                     <td className="px-5 py-4 text-right font-mono text-text-secondary">45</td>
                     <td className="px-5 py-4 text-right font-mono text-text-secondary">1,502.40</td>
                     <td className="px-5 py-4 text-right font-mono text-white">1,544.10</td>
                     <td className="px-5 py-4 text-right font-mono text-emerald-accent font-medium flex items-center justify-end gap-1">
                       <ArrowUpRight className="w-3 h-3" /> +1,876.50 (+2.7%)
                     </td>
                     <td className="px-5 py-4 text-right font-mono text-danger-accent group cursor-pointer">
                        <div className="flex items-center justify-end gap-2">
                           1,450.00 <Edit3 className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                     </td>
                     <td className="px-5 py-4 text-right">
                       <div className="flex items-center justify-end gap-2">
                         <button className="px-3 py-1.5 rounded-lg border border-blue-500/50 text-blue-400 hover:bg-blue-500/10 text-xs font-medium transition">Mod</button>
                         <button className="px-3 py-1.5 rounded-lg border border-danger-accent/50 text-danger-accent hover:bg-danger-accent/10 text-xs font-medium transition">Close</button>
                       </div>
                     </td>
                   </tr>
                   <tr className="bg-[#0F1623] hover:bg-slate-700/50 transition-colors">
                     <td className="px-5 py-4 font-bold text-white">HDFCBANK</td>
                     <td className="px-5 py-4 text-right font-mono text-text-secondary">120</td>
                     <td className="px-5 py-4 text-right font-mono text-text-secondary">1,450.00</td>
                     <td className="px-5 py-4 text-right font-mono text-white">1,432.50</td>
                     <td className="px-5 py-4 text-right font-mono text-danger-accent font-medium flex items-center justify-end gap-1">
                       <TrendingDown className="w-3 h-3" /> -2,100.00 (-1.2%)
                     </td>
                     <td className="px-5 py-4 text-right font-mono text-danger-accent group cursor-pointer">
                        <div className="flex items-center justify-end gap-2">
                           1,400.00 <Edit3 className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                     </td>
                     <td className="px-5 py-4 text-right">
                       <div className="flex items-center justify-end gap-2">
                         <button className="px-3 py-1.5 rounded-lg border border-blue-500/50 text-blue-400 hover:bg-blue-500/10 text-xs font-medium transition">Mod</button>
                         <button className="px-3 py-1.5 rounded-lg border border-danger-accent/50 text-danger-accent hover:bg-danger-accent/10 text-xs font-medium transition">Close</button>
                       </div>
                     </td>
                   </tr>
                 </tbody>
               </table>
             </div>
          </div>
        </div>

        {/* Right Sidebar - Trade Panel (1/3) */}
        <div className="w-full lg:w-1/3">
          <div className="p-6 rounded-2xl bg-slate-800 border border-border-subtle sticky top-24">
            <h2 className="text-sm font-bold text-text-muted uppercase tracking-wider mb-6">Live Trade Panel</h2>
            
            <div className="space-y-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                <input 
                  type="text" 
                  placeholder="Search Ticker (NSE/BSE)"
                  className="w-full pl-9 pr-4 py-3 rounded-xl bg-[#111827] border border-[#1E2D45] text-white text-sm focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div className="flex justify-between items-center p-4 rounded-xl border border-border-subtle bg-[#111827]">
                 <div>
                    <h3 className="font-bold text-white text-lg leading-tight">ZOMATO</h3>
                    <span className="text-xs text-text-muted">NSE</span>
                 </div>
                 <div className="text-right">
                    <div className="font-mono font-bold text-white text-lg">164.20</div>
                    <div className="text-xs text-emerald-accent font-medium">+2.40 (1.4%)</div>
                 </div>
              </div>

              <div className="flex p-1 bg-[#111827] rounded-lg border border-[#1E2D45]">
                <button 
                  onClick={() => setTradeAction("Buy")}
                  className={cn("flex-1 py-1.5 rounded-md text-sm font-bold transition-colors", tradeAction === "Buy" ? "bg-emerald-600 text-white" : "text-text-secondary hover:text-white")}
                >
                  BUY
                </button>
                <button 
                  onClick={() => setTradeAction("Sell")}
                  className={cn("flex-1 py-1.5 rounded-md text-sm font-bold transition-colors", tradeAction === "Sell" ? "bg-danger-accent text-white" : "text-text-secondary hover:text-white")}
                >
                  SELL
                </button>
              </div>

              <div>
                <label className="block text-xs font-medium text-text-muted mb-2 uppercase tracking-wide">Quantity</label>
                <input 
                  type="number" 
                  className="w-full px-4 py-3 rounded-xl bg-[#111827] border border-[#1E2D45] text-white font-mono focus:outline-none focus:border-blue-500 transition-colors"
                  defaultValue={100}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-text-muted mb-2 uppercase tracking-wide">Order Type</label>
                <div className="flex gap-2">
                  {["Market", "Limit", "SL"].map(t => (
                    <button 
                      key={t}
                      onClick={() => setOrderType(t)}
                      className={cn(
                        "flex-1 py-2 text-xs font-medium rounded-lg border transition-colors",
                        orderType === t ? "bg-slate-700 text-white border-slate-500" : "bg-[#111827] border-[#1E2D45] text-text-secondary hover:text-white"
                      )}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t border-border-subtle flex justify-between items-center mb-6">
                <span className="text-text-secondary text-sm">Margin Required</span>
                <span className="text-white font-mono font-bold text-lg">₹16,420.00</span>
              </div>

              <button 
                className={cn(
                  "w-full py-4 rounded-xl font-bold text-white shadow-lg transition-transform hover:-translate-y-0.5",
                  tradeAction === "Buy" ? "bg-emerald-600 hover:bg-emerald-500 shadow-[0_0_20px_rgba(16,185,129,0.3)]" : "bg-danger-accent hover:bg-red-400 shadow-[0_0_20px_rgba(239,68,68,0.3)]"
                )}
              >
                Execute Paper Trade
              </button>
              
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
