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
        setLogin(email, {
          id: "1",
          email,
          first_name: fullName.split(" ")[0] || "Trader",
          last_name: fullName.split(" ")[1] || ""
        });
        router.push("/onboarding");
      } else {
        const response: any = await apiRegister({
          email,
          full_name: fullName,
        });
        
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
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center shadow-sm">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-bold text-slate-900 tracking-tight">FinVoice</span>
          </div>
        </div>

        <div className="bg-white border border-slate-200 p-8 rounded-2xl shadow-sm">
          <h2 className="text-2xl font-bold text-slate-900 mb-2 text-center">
            {isLogin ? "Welcome Back" : "Create Account"}
          </h2>
          <p className="text-slate-500 text-sm mb-6 text-center">
            {isLogin 
              ? "Enter your details to access your dashboard" 
              : "Sign up to start your AI-powered investment journey"}
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 p-3 rounded-xl text-sm mb-6 text-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">Full Name</label>
                <input 
                  type="text" 
                  required={!isLogin}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                  placeholder="John Doe"
                />
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Email Address</label>
              <input 
                type="email" 
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                placeholder="you@example.com"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Password</label>
              <input 
                type="password" 
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-xl px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                placeholder="••••••••"
              />
            </div>

            <button 
              type="submit" 
              disabled={isLoading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition-all shadow-sm disabled:opacity-50 mt-4"
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
              className="text-slate-500 hover:text-slate-900 text-sm transition-colors"
            >
              {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-slate-400 mt-6 max-w-sm mx-auto">
          By continuing, you agree to our Terms of Service and acknowledge our Privacy Policy.
        </p>
      </div>
    </div>
  );
}
