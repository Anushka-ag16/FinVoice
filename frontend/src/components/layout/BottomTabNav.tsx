"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Home, PieChart, PlusCircle, Activity, Mic } from "lucide-react";

// Mobile uses a subset of tabs
const mobileTabs = [
  { name: "Home", href: "/", icon: Home },
  { name: "Portfolio", href: "/portfolio", icon: PieChart },
  { name: "Invest", href: "/new-investment", icon: PlusCircle, isPrimary: true },
  { name: "Simulation", href: "/stress-test", icon: Activity },
  { name: "Advisor", href: "/advisor", icon: Mic },
];

export function BottomTabNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-slate-800/80 backdrop-blur-lg border-t border-[#1E2D45] z-50 flex items-center justify-around px-2 pb-safe">
      {mobileTabs.map((tab) => {
        const isActive = pathname === tab.href || (tab.href !== "/" && pathname.startsWith(tab.href));
        
        if (tab.isPrimary) {
          return (
            <Link key={tab.name} href={tab.href} className="relative -top-5 flex flex-col items-center">
              <div className="flex items-center justify-center w-14 h-14 rounded-full bg-blue-600 text-white shadow-[0_0_15px_rgba(59,130,246,0.5)] border-4 border-[#090E1A]">
                <tab.icon className="w-6 h-6" />
              </div>
            </Link>
          );
        }

        return (
          <Link
            key={tab.name}
            href={tab.href}
            className={cn(
              "flex flex-col items-center justify-center w-16 h-full gap-1 transition-colors",
              isActive ? "text-blue-500" : "text-slate-400 hover:text-white"
            )}
          >
            <tab.icon className={cn("w-5 h-5", isActive ? "text-blue-500" : "text-slate-400")} />
            <span className="text-[10px] font-medium">{tab.name}</span>
          </Link>
        );
      })}
    </nav>
  );
}
