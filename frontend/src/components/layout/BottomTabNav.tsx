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
    <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-white border-t border-slate-200 z-50 flex items-center justify-around px-2 pb-safe shadow-[0_-1px_8px_rgba(0,0,0,0.06)]">
      {mobileTabs.map((tab) => {
        const isActive = pathname === tab.href || (tab.href !== "/" && pathname.startsWith(tab.href));
        
        if (tab.isPrimary) {
          return (
            <Link key={tab.name} href={tab.href} className="relative -top-5 flex flex-col items-center">
              <div className="flex items-center justify-center w-14 h-14 rounded-full bg-blue-600 text-white shadow-md border-4 border-white">
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
              isActive ? "text-blue-600" : "text-slate-400 hover:text-slate-700"
            )}
          >
            <tab.icon className={cn("w-5 h-5", isActive ? "text-blue-600" : "text-slate-400")} />
            <span className="text-[10px] font-medium">{tab.name}</span>
          </Link>
        );
      })}
    </nav>
  );
}
