"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity, Archive, ClipboardCheck, Clapperboard, Film, FileText,
  LayoutDashboard, Newspaper, Palette, Radio, Send, Settings, Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NAV_GROUPS } from "@/lib/constants";

const ICONS: Record<string, LucideIcon> = {
  LayoutDashboard, Activity, Newspaper, Palette, ClipboardCheck, Send, Archive,
  Settings, Clapperboard, Zap, FileText, Film,
};

function active(pathname: string, href: string): boolean {
  if (href === "/reels") return pathname === "/reels";
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname === href || pathname.startsWith(href + "/");
}

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-[232px] shrink-0 h-screen sticky top-0 border-r border-line bg-bg-soft/60 backdrop-blur-sm flex flex-col">
      <div className="px-5 pt-6 pb-5">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-teal/15 border border-teal/40 grid place-items-center">
            <Radio size={16} className="text-teal" />
          </div>
          <div className="leading-tight">
            <div className="text-[15px] font-semibold tracking-tight">Maven</div>
            <div className="text-[10px] uppercase tracking-[0.16em] text-ink-faint">Newsroom OS</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 space-y-4 overflow-auto pb-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="px-3 mb-1 text-[10px] uppercase tracking-[0.16em] text-ink-faint">
              {group.label}
            </div>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = ICONS[item.icon] || LayoutDashboard;
                const isActive = active(pathname, item.href);
                return (
                  <Link key={item.href} href={item.href}
                    className={`group flex items-center gap-3 rounded-lg px-3 py-1.5 text-[13px] transition-colors ${
                      isActive ? "bg-teal/10 text-ink border border-teal/25"
                               : "text-ink-muted hover:text-ink hover:bg-white/[0.04] border border-transparent"}`}>
                    <Icon size={15} className={isActive ? "text-teal" : "text-ink-faint group-hover:text-ink-muted"} />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-line">
        <div className="eyebrow mb-1">Schedule</div>
        <div className="text-sm font-medium">Closing Bell</div>
        <div className="text-xs text-ink-muted">5:00 PM IST · Mon–Fri</div>
      </div>
    </aside>
  );
}
