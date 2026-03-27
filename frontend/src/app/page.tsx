import Link from "next/link";
import { ArrowRight, Brain, Activity, Mic, Check, X } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 justify-center flex flex-col items-center text-center">
        {/* Abstract background mesh effect setup */}
        <div className="absolute inset-0 z-0 bg-navy overflow-hidden">
          <div className="absolute top-[20%] left-[50%] w-[800px] h-[800px] bg-brand-glow blur-[120px] rounded-full -translate-x-1/2" />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-4">
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
            Your <span className="text-gradient">AI-Powered</span> <br className="hidden md:block" />
            Financial Advisor
          </h1>
          <p className="text-lg md:text-xl text-text-secondary mb-10 max-w-2xl mx-auto">
            Institutional-grade portfolio management for every Indian investor. Free forever, upgraded when you need it.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link 
              href="/onboarding" 
              className="px-8 py-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-lg flex items-center gap-2 transition-all shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:shadow-[0_0_30px_rgba(59,130,246,0.5)]"
            >
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
            <Link 
              href="#how-it-works"
              className="px-8 py-4 rounded-xl border border-blue-500 text-blue-400 hover:bg-blue-600/10 font-medium text-lg transition-all"
            >
              See How It Works
            </Link>
          </div>
        </div>

        {/* Dashboard Preview Mockup */}
        <div className="relative z-10 w-full max-w-5xl mx-auto mt-20 px-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md overflow-hidden shadow-[0_0_50px_rgba(59,130,246,0.15)] aspect-video relative flex items-center justify-center">
            {/* Simple mockup visual */}
            <div className="absolute inset-0 flex flex-col">
              <div className="h-12 border-b border-white/10 flex items-center px-4 gap-2">
                <div className="w-3 h-3 rounded-full bg-slate-600" />
                <div className="w-3 h-3 rounded-full bg-slate-600" />
                <div className="w-3 h-3 rounded-full bg-slate-600" />
              </div>
              <div className="flex-1 p-8 flex gap-6">
                <div className="w-64 h-full bg-slate-800/50 rounded-xl" />
                <div className="flex-1 flex flex-col gap-6">
                  <div className="h-32 bg-slate-800/50 rounded-xl flex items-center px-8">
                     <span className="text-4xl font-mono text-white">₹4,83,200</span>
                  </div>
                  <div className="flex-1 flex gap-6">
                    <div className="flex-1 border border-border-subtle rounded-xl bg-slate-800/30" />
                    <div className="flex-1 border border-border-subtle rounded-xl bg-slate-800/30" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Strip */}
      <section id="how-it-works" className="py-20 bg-slate-800/50 border-y border-border-subtle relative z-10">
        <div className="max-w-7xl mx-auto px-4 grid md:grid-cols-3 gap-8">
          <div className="p-8 rounded-2xl bg-slate-800 border border-border-subtle transition-transform hover:-translate-y-1 hover:shadow-[0_0_20px_rgba(59,130,246,0.15)]">
            <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center mb-6">
              <Brain className="w-6 h-6 text-blue-500" />
            </div>
            <h3 className="text-xl font-bold text-white mb-3">Risk-Aware AI</h3>
            <p className="text-text-secondary leading-relaxed">
              Adaptive questionnaire that evolves with your financial goals for deep personalized risk profiling.
            </p>
          </div>
          
          <div className="p-8 rounded-2xl bg-slate-800 border border-border-subtle transition-transform hover:-translate-y-1 hover:shadow-[0_0_20px_rgba(16,185,129,0.15)]">
            <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center mb-6">
              <Activity className="w-6 h-6 text-emerald-500" />
            </div>
            <h3 className="text-xl font-bold text-white mb-3">Real-Time Rebalancing</h3>
            <p className="text-text-secondary leading-relaxed">
              Instant drift detection and automated portfolio adjustments to maintain your target asset allocation.
            </p>
          </div>

          <div className="p-8 rounded-2xl bg-slate-800 border border-border-subtle transition-transform hover:-translate-y-1 hover:shadow-[0_0_20px_rgba(168,85,247,0.15)]">
            <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mb-6">
              <Mic className="w-6 h-6 text-purple-500" />
            </div>
            <h3 className="text-xl font-bold text-white mb-3">Voice Advisory</h3>
            <p className="text-text-secondary leading-relaxed">
              Integrated Vapi voice agent for instant financial advice via natural conversation on the go.
            </p>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-12 border-b border-border-subtle relative z-10 flex flex-col items-center">
        <h4 className="text-sm font-bold tracking-widest text-text-muted uppercase mb-8">
          Built for 140M+ Indian Retail Investors
        </h4>
        <div className="flex flex-wrap justify-center gap-12 text-2xl font-bold font-mono text-text-secondary">
          <div className="flex items-center gap-2"><span>NSE</span><span className="text-text-muted text-sm">+1.2%</span></div>
          <div className="flex items-center gap-2"><span>BSE</span><span className="text-text-muted text-sm">+0.8%</span></div>
          <div className="flex items-center gap-2"><span>SEBI</span><span className="text-text-muted text-[10px] tracking-widest uppercase border border-text-muted rounded px-1">Regulated</span></div>
          <div className="flex items-center gap-2"><span>MCX</span><span className="text-text-muted text-sm">-0.4%</span></div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-24 relative z-10 flex flex-col items-center px-4">
        <h2 className="text-4xl md:text-5xl font-bold mb-4 text-center">Transparent Institutional Pricing</h2>
        <p className="text-text-secondary mb-16 text-center max-w-xl">Start for free and scale as your portfolio grows. No hidden commissions.</p>
        
        <div className="max-w-4xl w-full grid md:grid-cols-2 gap-8">
          {/* Free Tier */}
          <div className="p-8 rounded-2xl bg-slate-800 border border-blue-900/50 flex flex-col relative transition-transform hover:-translate-y-1">
            <h3 className="text-2xl font-bold mb-2">Free</h3>
            <div className="flex items-end gap-1 mb-6">
              <span className="text-4xl font-mono text-white">₹0</span>
              <span className="text-text-secondary pb-1">/forever</span>
            </div>
            <p className="text-text-secondary mb-8 h-12">Essential tools for the retail investor starting their journey.</p>
            
            <div className="space-y-4 mb-8 flex-1">
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-text-primary">Risk Assessment</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-text-primary">Portfolio Analysis</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-text-primary">Basic Rebalancing</span></div>
              <div className="flex items-center gap-3 opacity-40"><X className="w-5 h-5 text-text-muted" /> <span className="text-text-muted">Algo Trading</span></div>
              <div className="flex items-center gap-3 opacity-40"><X className="w-5 h-5 text-text-muted" /> <span className="text-text-muted">Voice Advisory</span></div>
            </div>
            
            <Link href="/onboarding" className="w-full py-3 rounded-xl border border-border-subtle text-white font-medium text-center hover:bg-slate-700 transition-colors">
              Start Free
            </Link>
          </div>

          {/* Pro Tier */}
          <div className="p-8 rounded-2xl bg-slate-800 border-2 border-transparent bg-clip-padding relative flex flex-col transition-transform hover:-translate-y-1">
            <div className="absolute inset-0 rounded-2xl border-2 border-transparent [background:linear-gradient(to_right,#3B82F6,#10B981)_border-box] [-webkit-mask:linear-gradient(#fff_0_0)_padding-box,linear-gradient(#fff_0_0)] [-webkit-mask-composite:destination-out] mask-composite-exclude pointer-events-none" />
            <div className="absolute top-0 right-8 -translate-y-1/2">
              <span className="px-3 py-1 bg-blue-600 text-white text-xs font-bold tracking-wider rounded-full uppercase shadow-[0_0_15px_rgba(59,130,246,0.5)]">Most Popular</span>
            </div>
            
            <h3 className="text-2xl font-bold mb-2">Pro</h3>
            <div className="flex items-end gap-1 mb-6">
              <span className="text-4xl font-mono text-white">₹299</span>
              <span className="text-text-secondary pb-1">/month</span>
            </div>
            <p className="text-text-secondary mb-8 h-12">Advanced intelligence for serious wealth management.</p>
            
            <div className="space-y-4 mb-8 flex-1">
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-text-primary">Risk Assessment</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-text-primary">Portfolio Analysis</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-text-primary">Crash Simulation</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-text-primary">Algo Trading</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-text-primary">Voice Advisory</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-text-primary">PDF Monthly Reports</span></div>
            </div>
            
            <Link href="/pricing" className="w-full py-3 rounded-xl bg-blue-200 text-blue-900 font-bold text-center hover:bg-blue-100 transition-colors relative overflow-hidden group">
              <div className="absolute inset-0 bg-white/20 -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
              Upgrade to Pro
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-border-subtle bg-navy py-12 px-4 relative z-10">
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-6 h-6 rounded bg-blue-600 flex items-center justify-center">
                <Activity className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-white">FinVoice</span>
            </div>
            <p className="text-sm text-text-muted">Democratizing institutional wealth management through advanced artificial intelligence for the modern Indian investor.</p>
          </div>
          <div>
            <h4 className="font-bold mb-4 text-white">Product</h4>
            <ul className="space-y-2 text-sm text-text-secondary">
              <li><Link href="/" className="hover:text-blue-400">Dashboard</Link></li>
              <li><Link href="/" className="hover:text-blue-400">Risk Engine</Link></li>
              <li><Link href="/" className="hover:text-blue-400">Algo Engine</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-4 text-white">Company</h4>
            <ul className="space-y-2 text-sm text-text-secondary">
              <li><Link href="/" className="hover:text-blue-400">About</Link></li>
              <li><Link href="/" className="hover:text-blue-400">Careers</Link></li>
              <li><Link href="/" className="hover:text-blue-400">Safety</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-4 text-white">Support</h4>
            <ul className="space-y-2 text-sm text-text-secondary">
              <li><Link href="/" className="hover:text-blue-400">Help Center</Link></li>
              <li><Link href="/" className="hover:text-blue-400">API Docs</Link></li>
              <li><Link href="/" className="hover:text-blue-400">Contact</Link></li>
            </ul>
          </div>
        </div>
        <div className="max-w-7xl mx-auto pt-8 border-t border-white/10 text-center text-xs text-text-muted">
          <p className="mb-2">DISCLAIMER: INVESTMENTS IN SECURITIES MARKET ARE SUBJECT TO MARKET RISKS. READ ALL THE RELATED DOCUMENTS CAREFULLY BEFORE INVESTING. REGISTRATION GRANTED BY SEBI, MEMBERSHIP OF BASL AND CERTIFICATION FROM NISM IN NO WAY GUARANTEE PERFORMANCE OF THE INTERMEDIARY OR PROVIDE ANY ASSURANCE OF RETURNS TO INVESTORS.</p>
          <p>&copy; 2024 Final Technologies Private Limited. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}
