"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { 
  Home, 
  PieChart, 
  PlusCircle, 
  Activity, 
  Mic, 
  TrendingUp, 
  FileText, 
  Settings 
} from "lucide-react";

const navItems = [
  { name: "Dashboard", href: "/", icon: Home },
  { name: "Portfolio", href: "/portfolio", icon: PieChart },
  { name: "New Investment", href: "/new-investment", icon: PlusCircle },
  { name: "Stress Test", href: "/stress-test", icon: Activity },
  { name: "AI Advisor", href: "/advisor", icon: Mic },
  { name: "Trading", href: "/trading", icon: TrendingUp },
  { name: "Reports", href: "/reports", icon: FileText },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex flex-col w-64 h-screen fixed left-0 top-0 bg-slate-800/50 backdrop-blur-md border-r border-[#1E2D45] z-50">
      <div className="flex items-center h-16 px-6 border-b border-[#1E2D45]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">FinVoice</span>
        </div>
      </div>
      
      <nav className="flex-1 py-6 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 group",
                isActive 
                  ? "bg-blue-600/10 text-blue-500 border-l-2 border-blue-500" 
                  : "text-slate-400 hover:text-white hover:bg-slate-700/50 border-l-2 border-transparent"
              )}
            >
              <item.icon className={cn("w-5 h-5", isActive ? "text-blue-500" : "text-slate-400 group-hover:text-white")} />
              <span className="font-medium text-sm">{item.name}</span>
            </Link>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-[#1E2D45]">
        <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-slate-700/30 border border-[#1E2D45]">
          <div className="w-8 h-8 rounded-full bg-slate-600 flex items-center justify-center text-white text-sm font-medium">
            AR
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">Arjun</p>
            <p className="text-xs text-slate-400 truncate">Free Plan</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
