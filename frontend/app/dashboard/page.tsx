"use client";

import Link from "next/link";
import { Activity, BarChart3, Plus, RefreshCw } from "lucide-react";

import { DecisionsChart } from "@/components/dashboard/decisions-chart";
import { KpiCards, PipelineHealth } from "@/components/dashboard/kpi-cards";
import { RecentRunsTable } from "@/components/dashboard/recent-runs-table";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const stats = useAsync(() => api.dashboardStats(), []);
  const initialLoading = stats.loading && !stats.data;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Command centre"
        title="Dashboard"
        description="Portfolio overview of applications, decisions and underwriting runs."
        meta={
          stats.data ? (
            <Badge variant="brand" dot>
              {stats.data.runs_total} runs
            </Badge>
          ) : null
        }
        actions={
          <>
            <Button variant="outline" size="sm" onClick={stats.reload} disabled={stats.loading}>
              <RefreshCw className={stats.loading ? "animate-spin" : undefined} /> Refresh
            </Button>
            <Button asChild size="sm">
              <Link href="/applications/new">
                <Plus /> New application
              </Link>
            </Button>
          </>
        }
      />

      {stats.error ? (
        <Alert variant="destructive" title="Could not load dashboard">
          {stats.error}
        </Alert>
      ) : null}

      {/* Hero KPI row */}
      {initialLoading ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[118px] rounded-lg" />
          ))}
        </div>
      ) : stats.data ? (
        <KpiCards stats={stats.data} />
      ) : null}

      {/* Wide chart + pipeline health */}
      <div className="grid gap-6 lg:grid-cols-12">
        <Card className="lg:col-span-8">
          <CardHeader>
            <SectionHeading
              icon={<BarChart3 />}
              title="Decisions by day"
              description="Approved, declined and referred outcomes per day."
            />
          </CardHeader>
          <CardContent>
            {initialLoading ? (
              <Skeleton className="h-72" />
            ) : (
              <DecisionsChart data={stats.data?.decisions_by_day ?? []} />
            )}
          </CardContent>
        </Card>

        {initialLoading ? (
          <Skeleton className="h-full min-h-[280px] rounded-lg lg:col-span-4" />
        ) : stats.data ? (
          <PipelineHealth stats={stats.data} className="lg:col-span-4" />
        ) : null}
      </div>

      {/* Recent runs */}
      <Card>
        <CardHeader>
          <SectionHeading
            icon={<Activity />}
            title="Recent runs"
            description="Latest underwriting runs across all applications."
            actions={
              <Button asChild variant="ghost" size="sm">
                <Link href="/review">Open review queue</Link>
              </Button>
            }
          />
        </CardHeader>
        <CardContent className="p-0">
          {initialLoading ? (
            <div className="p-5">
              <Skeleton className="h-64" />
            </div>
          ) : (
            <RecentRunsTable runs={stats.data?.recent_runs ?? []} />
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
