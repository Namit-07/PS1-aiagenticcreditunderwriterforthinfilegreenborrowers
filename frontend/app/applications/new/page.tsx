"use client";

import { ApplicationForm } from "@/components/applications/application-form";
import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";

export default function NewApplicationPage() {
  return (
    <AppShell>
      <PageHeader
        crumbs={[{ label: "Applications", href: "/applications" }, { label: "New" }]}
        eyebrow="Step 1 of 2"
        title="New application"
        description="Capture the product request and borrower details. You will upload documents next."
      />
      <ApplicationForm />
    </AppShell>
  );
}
