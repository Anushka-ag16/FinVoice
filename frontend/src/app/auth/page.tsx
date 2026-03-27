"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Activity } from "lucide-react";
import { apiRegister } from "@/lib/api";
import { useFinStore } from "@/store/useFinStore";

export default function AuthPage() {
  const router = useRouter();
  const setLogin = useFinStore((state) => state.login);
  
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      if (isLogin) {
        // In a real scenario we'd call apiLogin here, but backend uses JWT based auth which currently uses email as token.
        // I will mock this by setting token = email.
        setLogin(email, {
          id: "1",
          email,
          first_name: fullName.split(" ")[0] || "Trader",
          last_name: fullName.split(" ")[1] || ""
        });
        router.push("/onboarding");
      } else {
        // Register Real Call
        const response: any = await apiRegister({
          email,
          full_name: fullName,
        });
        
        // Use returned user
        setLogin(email, {
          id: response.id || "2",
          email: response.email,
          first_name: response.full_name?.split(" ")[0] || "Trader",
          last_name: ""
        });
        router.push("/onboarding");
      }
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background elements */}
      <div className="absolute top-[20%] left-[50%] w-[800px] h-[800px] bg-brand-glow blur-[120px] rounded-full -translate-x-1/2 opacity-50 pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center shadow-[0_0_15px_rgba(59,130,246,0.5)]">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-bold text-white tracking-tight">FinVoice</span>
          </div>
        </div>

        <div className="bg-slate-800/80 backdrop-blur-xl border border-white/10 p-8 rounded-2xl shadow-2xl">
          <h2 className="text-2xl font-bold text-white mb-2 text-center">
            {isLogin ? "Welcome Back" : "Create Account"}
          </h2>
          <p className="text-text-secondary text-sm mb-6 text-center">
            {isLogin 
              ? "Enter your details to access your dashboard" 
              : "Sign up to start your AI-powered investment journey"}
          </p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-3 rounded-xl text-sm mb-6 text-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">Full Name</label>
                <input 
                  type="text" 
                  required={!isLogin}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                  placeholder="John Doe"
                />
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">Email Address</label>
              <input 
                type="email" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                placeholder="you@example.com"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">Password</label>
              <input 
                type="password" 
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                placeholder="••••••••"
              />
            </div>

            <button 
              type="submit" 
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-xl transition-all shadow-[0_0_15px_rgba(59,130,246,0.3)] disabled:opacity-50 mt-4"
            >
              {isLoading ? "Processing..." : (isLogin ? "Sign In" : "Sign Up")}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button 
              onClick={() => {
                setIsLogin(!isLogin);
                setError("");
              }}
              className="text-text-secondary hover:text-white text-sm transition-colors"
            >
              {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
