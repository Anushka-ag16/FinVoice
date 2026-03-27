import { AlertTriangle, TrendingDown, ArrowRightLeft, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";

export default function PortfolioAnalyzerPage() {
  const correlations = [
    [1.0, 0.82, 0.41, 0.12, 0.05],
    [0.82, 1.0, 0.35, 0.18, 0.08],
    [0.41, 0.35, 1.0, 0.62, 0.15],
    [0.12, 0.18, 0.62, 1.0, 0.76],
    [0.05, 0.08, 0.15, 0.76, 1.0],
  ];
  
  const stocks = ["RELIANCE", "HDFCBANK", "INFY", "TCS", "ICICIBANK"];
  
  const getCorrelationColor = (val: number) => {
    if (val === 1) return "bg-slate-700 text-slate-400"; // self
    if (val >= 0.75) return "bg-danger-accent/20 text-danger-accent border-danger-accent shadow-[0_0_10px_rgba(239,68,68,0.3)] border";
    if (val >= 0.5) return "bg-warning-accent/20 text-warning-accent";
    return "bg-emerald-accent/10 text-emerald-accent";
  };

  return (
    <div className="flex flex-col gap-8 pb-20 md:pb-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white mb-2">
            Portfolio Deep Dive
          </h1>
          <p className="text-sm text-text-secondary font-medium">Last updated: Today, 09:41 AM</p>
        </div>
        <button className="px-4 py-2 rounded-xl bg-slate-800 border border-border-subtle text-white font-medium hover:bg-slate-700 transition">
          Export Report
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle">
          <span className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2 block">Portfolio Beta vs NIFTY50</span>
          <div className="flex items-end gap-3 mt-4">
            <span className="text-4xl font-bold font-mono text-warning-accent">1.28</span>
            <span className="px-2 py-1 bg-warning-accent/20 text-warning-accent text-xs rounded mb-1">High Volatility</span>
          </div>
          <div className="mt-4 pt-4 border-t border-border-subtle flex items-center justify-between text-xs text-text-muted">
            <span>Threshold: 1.20</span>
            <span className="text-warning-accent">Exceeded</span>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle">
          <span className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2 block">Sharpe Ratio (1Y)</span>
          <div className="flex items-end gap-3 mt-4">
            <span className="text-4xl font-bold font-mono text-white">0.91</span>
            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded mb-1">Good</span>
          </div>
          <div className="mt-4 pt-4 border-t border-border-subtle flex items-center justify-between text-xs text-text-muted">
            <span>Threshold: &gt; 0.80</span>
            <span className="text-emerald-accent">Healthy</span>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-800 border border-border-subtle">
          <span className="text-xs font-bold text-text-muted uppercase tracking-wider mb-2 block">Max Drawdown (1Y)</span>
          <div className="flex items-end gap-3 mt-4">
            <span className="text-4xl font-bold font-mono text-danger-accent flex items-center">
              -18.4%
            </span>
            <TrendingDown className="w-6 h-6 text-danger-accent mb-1" />
          </div>
          <div className="mt-4 pt-4 border-t border-border-subtle flex items-center justify-between text-xs text-text-muted">
            <span>March 2023 Low</span>
            <span className="text-text-secondary">Recovered in 42 days</span>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-slate-800 border border-border-subtle flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-white">Concentration Risk</h2>
            <span className="text-xs text-text-muted uppercase tracking-widest">Top 5 Holdings</span>
          </div>
          <div className="flex flex-col gap-4 flex-1 justify-center">
            {/* Horizontal Bar Chart Custom */}
            {[
              { name: "RELIANCE", val: 29.3, limit: 20 },
              { name: "HDFCBANK", val: 17.6, limit: 20 },
              { name: "INFY", val: 12.1, limit: 20 },
              { name: "TCS", val: 9.4, limit: 20 },
              { name: "ICICIBANK", val: 8.7, limit: 20 },
            ].map((st) => (
              <div key={st.name} className="flex flex-col gap-1">
                <div className="flex justify-between text-sm font-medium">
                  <span className="text-white">{st.name}</span>
                  <span className={cn("font-mono", st.val > st.limit ? "text-danger-accent" : "text-text-secondary")}>{st.val}%</span>
                </div>
                <div className="h-2 w-full bg-slate-700 rounded-full overflow-hidden relative">
                  <div 
                    className={cn("h-full rounded-full transition-all duration-1000", st.val > st.limit ? "bg-danger-accent" : "bg-blue-600")}
                    style={{ width: `${(st.val / 35) * 100}%` }}
                  />
                  <div className="absolute top-0 bottom-0 border-l-2 border-dashed border-danger-accent/50 z-10" style={{ left: `${(st.limit / 35) * 100}%` }} />
                </div>
                {st.val > st.limit && (
                  <span className="text-[10px] text-danger-accent font-bold uppercase mt-1 tracking-wider text-right">High Concentration</span>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-slate-800 border border-border-subtle">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-bold text-white">Sector Exposure</h2>
            <div className="flex items-center gap-1.5 px-2 py-1 bg-warning-accent/10 border border-warning-accent/20 text-warning-accent text-xs rounded font-medium">
              <AlertTriangle className="w-3.5 h-3.5" /> High Tech Exposure
            </div>
          </div>
          
          {/* Stacked Bar */}
          <div className="h-8 w-full rounded-lg overflow-hidden flex mb-8 border border-border-subtle">
            <div className="h-full bg-blue-500 transition-all hover:opacity-80 cursor-pointer" style={{ width: '38%' }} title="IT / Tech: 38%" />
            <div className="h-full bg-slate-500 transition-all hover:opacity-80 cursor-pointer" style={{ width: '25%' }} title="Financials: 25%" />
            <div className="h-full bg-emerald-500 transition-all hover:opacity-80 cursor-pointer" style={{ width: '15%' }} title="FMCG: 15%" />
            <div className="h-full bg-purple-500 transition-all hover:opacity-80 cursor-pointer" style={{ width: '10%' }} title="Healthcare: 10%" />
            <div className="h-full bg-warning-accent transition-all hover:opacity-80 cursor-pointer" style={{ width: '12%' }} title="Others: 12%" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-blue-500" />
                <span className="text-sm font-medium text-white">IT / Tech</span>
              </div>
              <span className="font-mono text-sm text-warning-accent">38.0%</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-slate-500" />
                <span className="text-sm font-medium text-white">Financials</span>
              </div>
              <span className="font-mono text-sm text-text-secondary">25.0%</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-emerald-500" />
                <span className="text-sm font-medium text-white">FMCG</span>
              </div>
              <span className="font-mono text-sm text-text-secondary">15.0%</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-purple-500" />
                <span className="text-sm font-medium text-white">Healthcare</span>
              </div>
              <span className="font-mono text-sm text-text-secondary">10.0%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-6 rounded-2xl bg-slate-800 border border-border-subtle overflow-x-auto">
        <h2 className="text-lg font-bold text-white mb-2">Correlation Heatmap</h2>
        <p className="text-sm text-text-secondary mb-6">Highly correlated pairs (≥ 0.75) may reduce diversification benefits.</p>

        <div className="min-w-[600px]">
          <div className="grid grid-cols-[100px_repeat(5,1fr)] gap-1 mb-1">
            <div />
            {stocks.map(s => <div key={s} className="text-xs font-bold text-text-muted text-center py-2">{s}</div>)}
          </div>
          {correlations.map((row, i) => (
            <div key={`row-${i}`} className="grid grid-cols-[100px_repeat(5,1fr)] gap-1 mb-1">
              <div className="text-xs font-bold text-text-muted flex items-center">{stocks[i]}</div>
              {row.map((val, j) => (
                <div 
                  key={`cell-${i}-${j}`} 
                  className={cn(
                    "flex items-center justify-center py-3 rounded text-sm font-mono transition-transform hover:scale-105 cursor-pointer",
                    getCorrelationColor(val)
                  )}
                  title={`${stocks[i]} & ${stocks[j]} Correlation: ${val}`}
                >
                  {val.toFixed(2)}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl bg-slate-800 border border-border-subtle overflow-hidden">
        <div className="p-6 border-b border-border-subtle pb-4 flex flex-col sm:flex-row justify-between sm:items-center gap-4">
          <div>
             <h2 className="text-lg font-bold text-white">Rupee Rebalancing Plan</h2>
             <p className="text-xs text-text-secondary mt-1">AI-optimized trades to correct drift and minimize taxes.</p>
          </div>
          <button className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium shadow-[0_0_15px_rgba(59,130,246,0.3)] transition shrink-0 flex items-center justify-center gap-2">
            Execute Trades <ArrowRightLeft className="w-4 h-4" />
          </button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-[#111827] border-b border-border-subtle text-text-muted uppercase text-[10px] tracking-wider font-bold">
              <tr>
                <th className="px-6 py-3">Action</th>
                <th className="px-6 py-3">Stock / Fund</th>
                <th className="px-6 py-3 text-right">Amount (₹)</th>
                <th className="px-6 py-3">Tax Impact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-subtle">
              <tr className="bg-[#0F1623]">
                <td className="px-6 py-4">
                  <span className="px-3 py-1 bg-danger-accent/10 border border-danger-accent/30 text-danger-accent font-bold rounded flex items-center gap-1 w-max">
                     SELL
                  </span>
                </td>
                <td className="px-6 py-4 font-medium text-white">RELIANCE</td>
                <td className="px-6 py-4 text-right font-mono">8,200</td>
                <td className="px-6 py-4">
                  <span className="text-danger-accent text-xs">₹620 STCG</span>
                </td>
              </tr>
              <tr className="bg-[#111827]">
                <td className="px-6 py-4">
                  <span className="px-3 py-1 bg-emerald-accent/10 border border-emerald-accent/30 text-emerald-accent font-bold rounded flex items-center gap-1 w-max">
                     BUY
                  </span>
                </td>
                <td className="px-6 py-4 font-medium text-white">SGB 2024-25</td>
                <td className="px-6 py-4 text-right font-mono">5,000</td>
                <td className="px-6 py-4">
                   <span className="text-text-secondary text-xs">—</span>
                </td>
              </tr>
              <tr className="bg-[#0F1623]">
                <td className="px-6 py-4">
                  <span className="px-3 py-1 bg-emerald-accent/10 border border-emerald-accent/30 text-emerald-accent font-bold rounded flex items-center gap-1 w-max">
                     BUY
                  </span>
                </td>
                <td className="px-6 py-4 font-medium text-white">PPFAS Flexi Cap</td>
                <td className="px-6 py-4 text-right font-mono">3,200</td>
                <td className="px-6 py-4">
                   <span className="text-text-secondary text-xs">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div className="bg-warning-accent/10 border-t border-warning-accent/20 p-4 flex gap-3">
          <ShieldAlert className="w-5 h-5 text-warning-accent shrink-0 mt-0.5" />
          <p className="text-sm text-text-primary">
            <span className="font-bold text-warning-accent block mb-1">Estimated tax event: ₹620 STCG</span>
            This sell order will generate short term capital gains. The assets turn long-term in 2 months. Consider waiting if you are in the highest tax bracket.
          </p>
        </div>
      </div>
      
    </div>
  );
}
