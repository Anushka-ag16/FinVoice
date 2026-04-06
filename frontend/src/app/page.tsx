import Link from "next/link";
import { ArrowRight, Brain, Activity, Mic, Check, X } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen bg-white">
      {/* Nav */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-slate-200 h-16 flex items-center px-6 md:px-12">
        <div className="flex items-center gap-2 flex-1">
          <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <Activity className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-slate-900 text-lg tracking-tight">FinVoice</span>
        </div>
        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
          <a href="#features" className="hover:text-slate-900 transition-colors">Features</a>
          <a href="#pricing" className="hover:text-slate-900 transition-colors">Pricing</a>
          <span className="text-xs px-2 py-0.5 rounded border border-slate-300 text-slate-500 uppercase tracking-wider font-medium">SEBI</span>
        </nav>
        <div className="flex items-center gap-3 ml-8">
          <Link href="/auth" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">Sign in</Link>
          <Link href="/auth" className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors">
            Get Started
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-40 pb-24 flex flex-col items-center text-center px-4">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-200 bg-blue-50 text-blue-700 text-xs font-semibold mb-8 uppercase tracking-wider">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
          SEBI Registered · AI-Powered · 140M+ Retail Investors
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-slate-900 mb-6 max-w-4xl leading-[1.08]">
          Your <span className="text-gradient">AI-Powered</span>{" "}
          <br className="hidden md:block" />
          Financial Advisor
        </h1>
        <p className="text-lg md:text-xl text-slate-500 mb-10 max-w-2xl mx-auto leading-relaxed">
          Institutional-grade portfolio management for every Indian investor. Free forever, upgraded when you need it.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link 
            href="/auth" 
            className="px-8 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-base flex items-center gap-2 transition-all shadow-sm"
          >
            Get Started Free <ArrowRight className="w-4 h-4" />
          </Link>
          <Link 
            href="#features"
            className="px-8 py-3.5 rounded-xl border border-[#CBD5E1] text-[#334155] hover:bg-slate-50 font-semibold text-base transition-all"
          >
            See How It Works
          </Link>
        </div>

        {/* Dashboard Preview Mockup */}
        <div className="w-full max-w-5xl mx-auto mt-20">
          <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-[0_4px_40px_rgba(0,0,0,0.08)] aspect-video relative">
            <div className="absolute inset-0 flex flex-col">
              {/* Mock browser chrome */}
              <div className="h-11 border-b border-slate-200 bg-slate-50 flex items-center px-4 gap-2">
                <div className="w-3 h-3 rounded-full bg-slate-300" />
                <div className="w-3 h-3 rounded-full bg-slate-300" />
                <div className="w-3 h-3 rounded-full bg-slate-300" />
                <div className="mx-4 flex-1 h-6 rounded bg-slate-200 max-w-xs" />
              </div>
              {/* Mock content */}
              <div className="flex-1 p-6 flex gap-5 bg-slate-50">
                <div className="w-52 h-full bg-white rounded-xl border border-slate-200" />
                <div className="flex-1 flex flex-col gap-5">
                  <div className="h-28 bg-white border border-slate-200 rounded-xl flex items-center px-8">
                    <div>
                      <div className="text-xs text-slate-400 font-medium mb-1 uppercase tracking-wider">Portfolio Value</div>
                      <span className="text-4xl font-mono text-slate-900 font-bold">₹4,83,200</span>
                      <span className="ml-3 text-sm text-emerald-600 font-semibold">+2.6%</span>
                    </div>
                  </div>
                  <div className="flex-1 flex gap-5">
                    <div className="flex-1 border border-slate-200 rounded-xl bg-white" />
                    <div className="flex-1 border border-slate-200 rounded-xl bg-white" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Strip */}
      <section id="features" className="py-20 bg-slate-50 border-y border-slate-200">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-3">Everything you need to invest smarter</h2>
            <p className="text-slate-500 text-lg max-w-xl mx-auto">Built for the modern Indian investor. No jargon. No commissions. Pure intelligence.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="p-8 rounded-2xl bg-white border border-slate-200 hover:-translate-y-1 transition-transform">
              <div className="w-11 h-11 bg-blue-100 rounded-xl flex items-center justify-center mb-6">
                <Brain className="w-5 h-5 text-blue-600" />
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Risk-Aware AI</h3>
              <p className="text-slate-500 leading-relaxed">
                Adaptive questionnaire that evolves with your financial goals for deep personalized risk profiling.
              </p>
            </div>
            
            <div className="p-8 rounded-2xl bg-white border border-slate-200 hover:-translate-y-1 transition-transform">
              <div className="w-11 h-11 bg-emerald-100 rounded-xl flex items-center justify-center mb-6">
                <Activity className="w-5 h-5 text-emerald-600" />
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Real-Time Rebalancing</h3>
              <p className="text-slate-500 leading-relaxed">
                Instant drift detection and automated portfolio adjustments to maintain your target asset allocation.
              </p>
            </div>

            <div className="p-8 rounded-2xl bg-white border border-slate-200 hover:-translate-y-1 transition-transform">
              <div className="w-11 h-11 bg-violet-100 rounded-xl flex items-center justify-center mb-6">
                <Mic className="w-5 h-5 text-violet-600" />
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Voice Advisory</h3>
              <p className="text-slate-500 leading-relaxed">
                Integrated Vapi voice agent for instant financial advice via natural conversation on the go.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section className="py-12 border-b border-slate-200 flex flex-col items-center bg-white">
        <h4 className="text-xs font-bold tracking-widest text-slate-400 uppercase mb-8">
          Built for 140M+ Indian Retail Investors
        </h4>
        <div className="flex flex-wrap justify-center gap-12 text-2xl font-bold font-mono text-slate-700">
          <div className="flex items-center gap-2"><span>NSE</span><span className="text-emerald-600 text-sm font-semibold">+1.2%</span></div>
          <div className="flex items-center gap-2"><span>BSE</span><span className="text-emerald-600 text-sm font-semibold">+0.8%</span></div>
          <div className="flex items-center gap-2"><span>SEBI</span><span className="text-slate-400 text-[10px] tracking-widest uppercase border border-slate-300 rounded px-1.5 py-0.5">Regulated</span></div>
          <div className="flex items-center gap-2"><span>MCX</span><span className="text-red-500 text-sm font-semibold">-0.4%</span></div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 flex flex-col items-center px-4 bg-white">
        <h2 className="text-4xl md:text-5xl font-bold mb-4 text-center text-slate-900">Transparent Institutional Pricing</h2>
        <p className="text-slate-500 mb-16 text-center max-w-xl">Start for free and scale as your portfolio grows. No hidden commissions.</p>
        
        <div className="max-w-4xl w-full grid md:grid-cols-2 gap-8">
          {/* Free Tier */}
          <div className="p-8 rounded-2xl bg-white border border-slate-200 flex flex-col hover:-translate-y-1 transition-transform">
            <h3 className="text-2xl font-bold text-slate-900 mb-2">Free</h3>
            <div className="flex items-end gap-1 mb-6">
              <span className="text-4xl font-mono text-slate-900 font-bold">₹0</span>
              <span className="text-slate-500 pb-1">/forever</span>
            </div>
            <p className="text-slate-500 mb-8 h-12">Essential tools for the retail investor starting their journey.</p>
            
            <div className="space-y-4 mb-8 flex-1">
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-slate-700">Risk Assessment</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-slate-700">Portfolio Analysis</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-emerald-500" /> <span className="text-slate-700">Basic Rebalancing</span></div>
              <div className="flex items-center gap-3 opacity-40"><X className="w-5 h-5 text-slate-400" /> <span className="text-slate-400">Algo Trading</span></div>
              <div className="flex items-center gap-3 opacity-40"><X className="w-5 h-5 text-slate-400" /> <span className="text-slate-400">Voice Advisory</span></div>
            </div>
            
            <Link href="/auth" className="w-full py-3 rounded-xl border border-slate-300 text-slate-700 font-semibold text-center hover:bg-slate-50 transition-colors">
              Start Free
            </Link>
          </div>

          {/* Pro Tier */}
          <div className="p-8 rounded-2xl bg-blue-50 border border-blue-200 flex flex-col hover:-translate-y-1 transition-transform relative">
            <div className="absolute top-0 right-8 -translate-y-1/2">
              <span className="px-3 py-1 bg-blue-600 text-white text-xs font-bold tracking-wider rounded-full uppercase">Most Popular</span>
            </div>
            
            <h3 className="text-2xl font-bold text-blue-900 mb-2">Pro</h3>
            <div className="flex items-end gap-1 mb-6">
              <span className="text-4xl font-mono text-blue-900 font-bold">₹299</span>
              <span className="text-blue-700 pb-1">/month</span>
            </div>
            <p className="text-blue-800 mb-8 h-12">Advanced intelligence for serious wealth management.</p>
            
            <div className="space-y-4 mb-8 flex-1">
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-blue-600" /> <span className="text-blue-900">Risk Assessment</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-blue-600" /> <span className="text-blue-900">Portfolio Analysis</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-blue-600" /> <span className="text-blue-900">Crash Simulation</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-blue-600" /> <span className="text-blue-900">Algo Trading</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-blue-600" /> <span className="text-blue-900">Voice Advisory</span></div>
              <div className="flex items-center gap-3"><Check className="w-5 h-5 text-blue-600" /> <span className="text-blue-900">PDF Monthly Reports</span></div>
            </div>
            
            <Link href="/pricing" className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-center transition-colors relative overflow-hidden group">
              <div className="absolute inset-0 bg-white/10 -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
              Upgrade to Pro
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 bg-slate-50 py-12 px-4">
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-6 h-6 rounded bg-blue-600 flex items-center justify-center">
                <Activity className="w-4 h-4 text-white" />
              </div>
              <span className="font-bold text-slate-900">FinVoice</span>
            </div>
            <p className="text-sm text-slate-500">Democratizing institutional wealth management through advanced artificial intelligence for the modern Indian investor.</p>
          </div>
          <div>
            <h4 className="font-bold mb-4 text-slate-900">Product</h4>
            <ul className="space-y-2 text-sm text-slate-500">
              <li><Link href="/" className="hover:text-blue-600 transition-colors">Dashboard</Link></li>
              <li><Link href="/" className="hover:text-blue-600 transition-colors">Risk Engine</Link></li>
              <li><Link href="/" className="hover:text-blue-600 transition-colors">Algo Engine</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-4 text-slate-900">Company</h4>
            <ul className="space-y-2 text-sm text-slate-500">
              <li><Link href="/" className="hover:text-blue-600 transition-colors">About</Link></li>
              <li><Link href="/" className="hover:text-blue-600 transition-colors">Careers</Link></li>
              <li><Link href="/" className="hover:text-blue-600 transition-colors">Safety</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold mb-4 text-slate-900">Support</h4>
            <ul className="space-y-2 text-sm text-slate-500">
              <li><Link href="/" className="hover:text-blue-600 transition-colors">Help Center</Link></li>
              <li><Link href="/" className="hover:text-blue-600 transition-colors">API Docs</Link></li>
              <li><Link href="/" className="hover:text-blue-600 transition-colors">Contact</Link></li>
            </ul>
          </div>
        </div>
        <div className="max-w-7xl mx-auto pt-8 border-t border-slate-200 text-center text-xs text-slate-400">
          <p className="mb-2">DISCLAIMER: INVESTMENTS IN SECURITIES MARKET ARE SUBJECT TO MARKET RISKS. READ ALL THE RELATED DOCUMENTS CAREFULLY BEFORE INVESTING. REGISTRATION GRANTED BY SEBI, MEMBERSHIP OF BASL AND CERTIFICATION FROM NISM IN NO WAY GUARANTEE PERFORMANCE OF THE INTERMEDIARY OR PROVIDE ANY ASSURANCE OF RETURNS TO INVESTORS.</p>
          <p>&copy; 2024 Final Technologies Private Limited. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}
