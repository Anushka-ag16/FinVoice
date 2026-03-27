"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { BottomTabNav } from "./BottomTabNav";

export function MainLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  
  // Hide sidebar/nav on root (Landing) and onboarding
  const isFullScreen = pathname === "/" || pathname === "/onboarding" || pathname === "/pricing";

  if (isFullScreen) {
    return <main className="flex-1 flex flex-col">{children}</main>;
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col md:pl-64 pb-16 md:pb-0">
        <main className="flex-1 flex flex-col max-w-[1280px] w-full mx-auto p-4 md:p-8">
          {children}
        </main>
      </div>
      <BottomTabNav />
    </div>
  );
}
