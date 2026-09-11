"use client";

import { Suspense, type ReactNode } from "react";

import { ApplicationNav } from "@/components/applications/application-nav";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader, type Crumb } from "@/components/layout/page-header";
import { shortId } from "@/lib/utils";

export interface ApplicationPageFrameProps {
  applicationId: string;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}

/**
 * Shell + breadcrumb + application sub-navigation, used by every /applications/[id]/* page.
 * The children are wrapped in Suspense because they typically call useSearchParams().
 */
export function ApplicationPageFrame({
  applicationId,
  title,
  description,
  actions,
  children,
}: ApplicationPageFrameProps) {
  const crumbs: Crumb[] = [
    { label: "Applications", href: "/applications" },
    { label: shortId(applicationId, 12), href: `/applications/${applicationId}` },
    { label: title },
  ];
  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <PageHeader
          crumbs={crumbs}
          eyebrow="Application file"
          title={title}
          description={description}
          actions={actions}
        />
        <Suspense fallback={<div className="h-11 rounded-lg border bg-muted/60" aria-hidden="true" />}>
          <ApplicationNav applicationId={applicationId} />
        </Suspense>
      </div>
      <Suspense fallback={null}>{children}</Suspense>
    </AppShell>
  );
}
