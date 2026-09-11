"use client";

import Link from "next/link";
import { FileText, Plus, RefreshCw } from "lucide-react";

import { ApplicationsTable } from "@/components/applications/applications-table";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import { SkeletonBlock } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";

export default function ApplicationsPage() {
  const apps = useAsync(() => api.listApplications(), []);
  const count = apps.data?.length ?? 0;

  return (
    <AppShell>
      <PageHeader
        eyebrow="Loan files"
        title="Applications"
        description="All loan applications. Click a row to open the application."
        meta={
          apps.data ? (
            <Badge variant="brand">
              {count} {count === 1 ? "application" : "applications"}
            </Badge>
          ) : null
        }
        actions={
          <>
            <Button variant="outline" size="sm" onClick={apps.reload} disabled={apps.loading}>
              <RefreshCw className={apps.loading ? "animate-spin" : undefined} /> Refresh
            </Button>
            <Button asChild size="sm">
              <Link href="/applications/new">
                <Plus /> New application
              </Link>
            </Button>
          </>
        }
      />
      {apps.error ? (
        <Alert variant="destructive" title="Could not load applications">
          {apps.error}
        </Alert>
      ) : null}
      <Card>
        <CardHeader className="border-b">
          <SectionHeading
            icon={<FileText />}
            title="All applications"
            description={apps.data ? `Showing ${count} ${count === 1 ? "record" : "records"}, newest activity first.` : "Loading applications…"}
          />
        </CardHeader>
        <CardContent className="p-0">
          {apps.loading && !apps.data ? (
            <div className="p-5">
              <SkeletonBlock lines={5} />
            </div>
          ) : (
            <ApplicationsTable applications={apps.data ?? []} />
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
