"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BrainCircuit,
  FileText,
  LayoutDashboard,
  Leaf,
  LogOut,
  Plus,
  Settings,
  UserCheck,
  type LucideIcon,
} from "lucide-react";

import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Button } from "@/components/ui/button";
import { SkeletonBlock } from "@/components/ui/skeleton";
import { clearSession, getToken, getUser } from "@/lib/session";
import type { AuthUser } from "@/lib/types";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  hint: string;
}

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, hint: "Portfolio overview" },
  { href: "/applications", label: "Applications", icon: FileText, hint: "Loan files" },
  { href: "/review", label: "Review queue", icon: UserCheck, hint: "Paused for a human" },
  { href: "/risk-model", label: "Risk model", icon: BrainCircuit, hint: "XGBoost metrics" },
  { href: "/settings", label: "Settings", icon: Settings, hint: "Policies & session" },
];

export interface AppShellProps {
  children: ReactNode;
}

function initials(user: AuthUser | null): string {
  const src = user?.name?.trim() || user?.email || "";
  if (!src) return "?";
  const parts = src.replace(/@.*$/, "").split(/[\s._-]+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}

/**
 * Shared authenticated layout: dark sidebar navigation + light content area.
 * Redirects to /login when no demo token is stored.
 */
export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setAuthed(false);
      router.replace("/login");
      return;
    }
    setUser(getUser());
    setAuthed(true);
  }, [router]);

  const logout = () => {
    clearSession();
    router.replace("/login");
  };

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar (desktop) */}
      <aside className="sticky top-0 hidden h-screen w-[248px] shrink-0 flex-col bg-sidebar text-sidebar-foreground md:flex">
        <Link href="/dashboard" className="flex items-center gap-3 px-5 pb-4 pt-5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-gradient text-white shadow-glow">
            <Leaf className="h-[18px] w-[18px]" />
          </span>
          <span className="leading-tight">
            <span className="block text-[15px] font-bold tracking-tight">Verdant</span>
            <span className="block text-[11px] text-sidebar-muted">AI Credit Underwriter</span>
          </span>
        </Link>

        <div className="px-4 pb-3">
          <Button asChild variant="brand" className="w-full justify-start">
            <Link href="/applications/new">
              <Plus /> New application
            </Link>
          </Button>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 px-3" aria-label="Main">
          <div className="px-2 pb-1.5 pt-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-sidebar-muted">
            Workspace
          </div>
          {NAV.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-sidebar-active text-white"
                    : "text-sidebar-muted hover:bg-white/5 hover:text-sidebar-foreground"
                )}
                aria-current={active ? "page" : undefined}
              >
                {active ? (
                  <span className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-lime" aria-hidden="true" />
                ) : null}
                <item.icon className={cn("h-4 w-4", active ? "text-lime" : "opacity-80 group-hover:opacity-100")} />
                <span className="flex-1">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-sidebar-border p-3">
          <div className="flex items-center gap-3 rounded-md px-2 py-1.5">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-white">
              {initials(user)}
            </span>
            <div className="min-w-0 flex-1 leading-tight">
              <div className="truncate text-[13px] font-medium text-white" title={user?.email}>
                {user?.name?.trim() || user?.email || "—"}
              </div>
              <div className="truncate text-[11px] text-sidebar-muted">{user?.role || "Underwriter"}</div>
            </div>
            <button
              type="button"
              onClick={logout}
              className="rounded-md p-1.5 text-sidebar-muted transition-colors hover:bg-white/10 hover:text-white"
              aria-label="Logout"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur-md md:px-8">
          <Link href="/dashboard" className="flex items-center gap-2 md:hidden">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-gradient text-white">
              <Leaf className="h-4 w-4" />
            </span>
            <span className="text-sm font-bold">Verdant</span>
          </Link>
          <div className="ml-auto flex items-center gap-1.5">
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={logout} className="md:hidden">
              <LogOut />
            </Button>
          </div>
        </header>

        {/* Mobile nav */}
        <nav className="flex gap-1 overflow-x-auto border-b bg-card px-2 py-1.5 md:hidden" aria-label="Main">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium",
                isActive(item.href) ? "bg-primary-soft text-primary" : "text-muted-foreground"
              )}
            >
              <item.icon className="h-3.5 w-3.5" />
              {item.label}
            </Link>
          ))}
        </nav>

        <main className="flex-1 px-4 py-6 md:px-8 md:py-8">
          {authed ? (
            <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-6 animate-in-up">{children}</div>
          ) : (
            <div className="mx-auto w-full max-w-[1280px]">
              <SkeletonBlock lines={4} />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
