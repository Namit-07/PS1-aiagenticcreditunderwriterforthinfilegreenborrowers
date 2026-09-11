"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Rocket, Scale, Server, ShieldCheck, UserRound } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { AiProviderCard } from "@/components/settings/ai-provider-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import { BASE_URL } from "@/lib/api";
import { clearSession, getUser } from "@/lib/session";
import type { AuthUser } from "@/lib/types";
import { cn } from "@/lib/utils";

const PROFILES = [
  { name: "default", foir: "0.50", ltv: "0.80", minAge: 21, text: "Balanced thresholds for the standard green-loan book." },
  { name: "conservative", foir: "0.40", ltv: "0.70", minAge: 23, text: "Tighter affordability and collateral cover; more referrals." },
  { name: "aggressive", foir: "0.60", ltv: "0.90", minAge: 18, text: "Growth setting with wider limits; relies more on the risk model." },
];

const PROFILE_ICON: Record<string, React.ReactNode> = {
  default: <Scale />,
  conservative: <ShieldCheck />,
  aggressive: <Rocket />,
};

function initials(user: AuthUser | null): string {
  const src = user?.name?.trim() || user?.email || "";
  if (!src) return "?";
  const parts = src.replace(/@.*$/, "").split(/[\s._-]+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join("");
}

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  useEffect(() => setUser(getUser()), []);

  const logout = () => {
    clearSession();
    router.replace("/login");
  };

  return (
    <AppShell>
      <PageHeader eyebrow="Workspace" title="Settings" description="Environment, policy profiles and session." />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Backend */}
        <Card className="flex flex-col">
          <CardHeader>
            <SectionHeading
              icon={<Server />}
              title="Backend"
              description="The API base URL comes from NEXT_PUBLIC_BACKEND_URL at build time."
            />
          </CardHeader>
          <CardContent className="flex flex-1 flex-col gap-3">
            <div className="rounded-md border bg-muted/50 p-3">
              <div className="eyebrow mb-1.5">Base URL</div>
              <code className="block break-all font-mono text-sm text-foreground">{BASE_URL}</code>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline" className="font-mono text-[11px]">
                NEXT_PUBLIC_BACKEND_URL
              </Badge>
              <span>Restart the dev server after changing it.</span>
            </div>
          </CardContent>
        </Card>

        {/* Session */}
        <Card className="flex flex-col">
          <CardHeader>
            <SectionHeading icon={<UserRound />} title="Session" description="Demo token stored in this browser only." />
          </CardHeader>
          <CardContent className="flex-1">
            <div className="flex items-center gap-4 rounded-md border bg-muted/50 p-3">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-brand-gradient text-sm font-bold text-white shadow-glow">
                {initials(user)}
              </span>
              <div className="min-w-0 flex-1 leading-tight">
                <div className="truncate text-[15px] font-semibold">{user?.name?.trim() || user?.email || "—"}</div>
                <div className="mt-0.5 truncate text-xs text-muted-foreground" title={user?.email}>
                  {user?.email ?? "—"}
                </div>
              </div>
              {user?.role ? (
                <Badge variant="brand" className="shrink-0 capitalize">
                  {user.role}
                </Badge>
              ) : (
                <Badge variant="muted" className="shrink-0">
                  No role
                </Badge>
              )}
            </div>
          </CardContent>
          <CardFooter className="justify-between gap-3">
            <span className="text-xs text-muted-foreground">Signing out clears the local demo token.</span>
            <Button variant="outline" size="sm" onClick={logout}>
              <LogOut /> Logout
            </Button>
          </CardFooter>
        </Card>
      </div>

      <AiProviderCard />

      {/* Policy profiles */}
      <div className="flex flex-col gap-4">
        <SectionHeading
          icon={<Scale />}
          title="Policy profiles"
          description="Selectable when starting a run or in what-if. Limits are enforced by the decision_policy node."
        />
        <div className="grid gap-4 md:grid-cols-3">
          {PROFILES.map((p, i) => {
            const isDefault = p.name === "default";
            return (
              <Card
                key={p.name}
                className={cn(
                  "relative flex flex-col overflow-hidden animate-in-up",
                  i === 1 && "delay-1",
                  i === 2 && "delay-2",
                  isDefault && "border-primary/40 shadow-glow"
                )}
              >
                {isDefault ? <span className="absolute inset-x-0 top-0 h-[3px] bg-brand-gradient" aria-hidden="true" /> : null}
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <span
                      className={cn(
                        "flex h-9 w-9 shrink-0 items-center justify-center rounded-md [&_svg]:h-4 [&_svg]:w-4",
                        isDefault ? "bg-primary text-primary-foreground" : "bg-primary-soft text-primary"
                      )}
                    >
                      {PROFILE_ICON[p.name]}
                    </span>
                    {isDefault ? <Badge variant="brand">Default</Badge> : null}
                  </div>
                  <div className="mt-3 text-[15px] font-semibold capitalize leading-tight tracking-tight">{p.name}</div>
                  <p className="text-[13px] leading-snug text-muted-foreground">{p.text}</p>
                </CardHeader>
                <CardContent className="flex-1 pt-0">
                  <dl className="divide-y rounded-md border bg-muted/40">
                    <div className="flex items-center justify-between px-3 py-2.5">
                      <dt className="text-xs text-muted-foreground">Max FOIR</dt>
                      <dd className="text-sm font-semibold tnum">{p.foir}</dd>
                    </div>
                    <div className="flex items-center justify-between px-3 py-2.5">
                      <dt className="text-xs text-muted-foreground">Max LTV</dt>
                      <dd className="text-sm font-semibold tnum">{p.ltv}</dd>
                    </div>
                    <div className="flex items-center justify-between px-3 py-2.5">
                      <dt className="text-xs text-muted-foreground">Min age</dt>
                      <dd className="text-sm font-semibold tnum">{p.minAge}</dd>
                    </div>
                  </dl>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </AppShell>
  );
}
