"use client";

import { useState } from "react";
import { Search, Trophy, TrendingUp, TrendingDown, Edit3, ArrowUpRight } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
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
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Virtual Wallet</span>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-slate-900">₹9,74,200</span>
              </div>
              <div className="text-[10px] text-slate-500 mt-1">Started ₹10.0L</div>
            </div>
            
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
               <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Unrealized P&L</span>
               <div className="text-xl font-bold font-mono text-emerald-accent">+₹23,400</div>
               <div className="text-[10px] text-emerald-accent mt-1">+2.4% Overall</div>
            </div>
            
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
               <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Sharpe Ratio</span>
               <div className="text-xl font-bold font-mono text-slate-900">0.73</div>
               <div className="text-[10px] text-blue-600 mt-1">Target &gt; 0.5</div>
            </div>
            
            <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-sm">
               <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1 block">Days Active</span>
               <div className="text-xl font-bold font-mono text-slate-900">14 / 30</div>
               <div className="text-[10px] text-slate-500 mt-1">To graduate</div>
            </div>
          </div>

          {/* Performance Chart */}
          <div className="p-5 rounded-2xl bg-white border border-slate-200 shadow-sm h-[300px] flex flex-col">
            <h2 className="text-sm font-bold text-slate-900 mb-4">Paper Performance vs NIFTY50</h2>
            <div className="flex-1 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={performanceData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPf" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="day" hide />
                  <YAxis domain={['dataMin - 10000', 'dataMax + 10000']} hide />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#fff', borderColor: '#E2E8F0', borderRadius: '8px', color: '#0F172A' }}
                    labelFormatter={() => ''}
                    formatter={(value: any) => [`₹${Math.round(Number(value)).toLocaleString('en-IN')}`]}
                  />
                  <Area type="monotone" dataKey="benchmark" stroke="#94A3B8" strokeDasharray="5 5" fill="none" name="NIFTY50" />
                  <Area type="monotone" dataKey="portfolio" stroke="#10B981" strokeWidth={2} fillOpacity={1} fill="url(#colorPf)" name="Your Paper Pf" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Graduate Card */}
          <div className="p-6 rounded-2xl bg-emerald-50 border border-emerald-200 flex flex-col sm:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center shrink-0 border border-emerald-200">
                <Trophy className="w-7 h-7 text-emerald-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 mb-1">You've earned your Live Trading Badge!</h3>
                <p className="text-sm text-slate-600">Your 30-day Sharpe: <strong className="text-slate-900">0.91</strong>. You've consistently beaten the baseline.</p>
              </div>
            </div>
            <button className="w-full sm:w-auto px-6 py-3 shrink-0 rounded-xl bg-gradient-to-r from-orange-500 to-gold-accent text-white font-bold transition-transform hover:scale-105 shadow-sm">
              Go Live Now
            </button>
          </div>

          {/* Active Positions Table */}
          <div className="rounded-2xl bg-white border border-slate-200 shadow-sm overflow-hidden">
             <div className="p-5 border-b border-slate-200">
               <h2 className="text-lg font-bold text-slate-900">Active Paper Positions</h2>
             </div>
             <div className="overflow-x-auto">
               <table className="w-full text-left text-sm whitespace-nowrap">
                 <thead className="bg-slate-50 border-b border-slate-200 text-slate-400">
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
                 <tbody className="divide-y divide-slate-100">
                   <tr className="bg-white hover:bg-slate-50 transition-colors">
                     <td className="px-5 py-4 font-bold text-slate-900">INFY</td>
                     <td className="px-5 py-4 text-right font-mono text-slate-500">45</td>
                     <td className="px-5 py-4 text-right font-mono text-slate-500">1,502.40</td>
                     <td className="px-5 py-4 text-right font-mono text-slate-900">1,544.10</td>
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
                         <button className="px-3 py-1.5 rounded-lg border border-blue-500/50 text-blue-600 hover:bg-blue-50 text-xs font-medium transition">Mod</button>
                         <button className="px-3 py-1.5 rounded-lg border border-danger-accent/50 text-danger-accent hover:bg-red-50 text-xs font-medium transition">Close</button>
                       </div>
                     </td>
                   </tr>
                   <tr className="bg-slate-50 hover:bg-slate-100 transition-colors">
                     <td className="px-5 py-4 font-bold text-slate-900">HDFCBANK</td>
                     <td className="px-5 py-4 text-right font-mono text-slate-500">120</td>
                     <td className="px-5 py-4 text-right font-mono text-slate-500">1,450.00</td>
                     <td className="px-5 py-4 text-right font-mono text-slate-900">1,432.50</td>
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
                         <button className="px-3 py-1.5 rounded-lg border border-blue-500/50 text-blue-600 hover:bg-blue-50 text-xs font-medium transition">Mod</button>
                         <button className="px-3 py-1.5 rounded-lg border border-danger-accent/50 text-danger-accent hover:bg-red-50 text-xs font-medium transition">Close</button>
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
          <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm sticky top-24">
            <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-6">Live Trade Panel</h2>
            
            <div className="space-y-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                  type="text" 
                  placeholder="Search Ticker (NSE/BSE)"
                  className="w-full pl-9 pr-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-900 placeholder:text-slate-400 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                />
              </div>

              <div className="flex justify-between items-center p-4 rounded-xl border border-slate-200 bg-slate-50">
                 <div>
                    <h3 className="font-bold text-slate-900 text-lg leading-tight">ZOMATO</h3>
                    <span className="text-xs text-slate-400">NSE</span>
                 </div>
                 <div className="text-right">
                    <div className="font-mono font-bold text-slate-900 text-lg">164.20</div>
                    <div className="text-xs text-emerald-accent font-medium">+2.40 (1.4%)</div>
                 </div>
              </div>

              <div className="flex p-1 bg-slate-100 rounded-lg border border-slate-200">
                <button 
                  onClick={() => setTradeAction("Buy")}
                  className={cn("flex-1 py-1.5 rounded-md text-sm font-bold transition-colors", tradeAction === "Buy" ? "bg-emerald-600 text-white shadow-sm" : "text-slate-500 hover:text-slate-900")}
                >
                  BUY
                </button>
                <button 
                  onClick={() => setTradeAction("Sell")}
                  className={cn("flex-1 py-1.5 rounded-md text-sm font-bold transition-colors", tradeAction === "Sell" ? "bg-danger-accent text-white shadow-sm" : "text-slate-500 hover:text-slate-900")}
                >
                  SELL
                </button>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 mb-2 uppercase tracking-wide">Quantity</label>
                <input 
                  type="number" 
                  className="w-full px-4 py-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-900 font-mono focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                  defaultValue={100}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-500 mb-2 uppercase tracking-wide">Order Type</label>
                <div className="flex gap-2">
                  {["Market", "Limit", "SL"].map(t => (
                    <button 
                      key={t}
                      onClick={() => setOrderType(t)}
                      className={cn(
                        "flex-1 py-2 text-xs font-medium rounded-lg border transition-colors",
                        orderType === t ? "bg-blue-600 text-white border-blue-500" : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-900 hover:border-slate-300"
                      )}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200 flex justify-between items-center mb-6">
                <span className="text-slate-500 text-sm">Margin Required</span>
                <span className="text-slate-900 font-mono font-bold text-lg">₹16,420.00</span>
              </div>

              <button 
                className={cn(
                  "w-full py-4 rounded-xl font-bold text-white shadow-sm transition-transform hover:-translate-y-0.5",
                  tradeAction === "Buy" ? "bg-emerald-600 hover:bg-emerald-500" : "bg-danger-accent hover:bg-red-500"
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
