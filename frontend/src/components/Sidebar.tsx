"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  FileText, 
  Send, 
  Settings, 
  LogOut,
  BarChart3,
  Activity
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { name: "Mission Control", href: "/jobs", icon: LayoutDashboard },
  { name: "Professional Context", href: "/profile", icon: FileText },
  { name: "Resume Infrastructure", href: "/resumes", icon: FileText },
  { name: "Application History", href: "/applications", icon: Send },
  { name: "Outcome Intelligence", href: "/intelligence", icon: BarChart3 },
  { name: "Operational Health", href: "/operations", icon: Activity },
  { name: "System Settings", href: "/settings", icon: Settings },
];

import { useRouter } from "next/navigation";
import { backendApi } from "@/lib/backend-api";
import { appConfig } from "@/lib/config";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      // Optional: Notify backend
      await backendApi.auth.logout().catch(() => {});
    } finally {
      // Clear tokens and redirect
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      router.push("/login");
    }
  };

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/50 flex flex-col h-screen sticky top-0">
      <div className="p-6">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
          {appConfig.appName}
        </h1>
      </div>

      <nav className="flex-1 px-4 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-4 py-2 rounded-lg transition-colors",
                isActive 
                  ? "bg-blue-600/10 text-blue-400 font-medium" 
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              )}
            >
              <item.icon size={20} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800">
        <button 
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-2 w-full text-slate-400 hover:text-red-400 transition-colors"
        >
          <LogOut size={20} />
          Logout
        </button>
      </div>
    </aside>
  );
}
