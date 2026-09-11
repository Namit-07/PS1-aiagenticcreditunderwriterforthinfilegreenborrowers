"use client";

import { use, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, Circle, FileUp, Files, ListChecks } from "lucide-react";

import { ApplicationPageFrame } from "@/components/applications/application-page-frame";
import { DocumentList } from "@/components/documents/document-list";
import { DocumentUploader } from "@/components/documents/document-uploader";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { SectionHeading } from "@/components/ui/section-heading";
import { SkeletonBlock } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/use-async";
import { api, errorMessage } from "@/lib/api";
import type { Document } from "@/lib/types";
import { cn } from "@/lib/utils";

interface PageProps {
  params: Promise<{ id: string }>;
}

const EXPECTED: { category: string; label: string; hint: string }[] = [
  { category: "kyc", label: "KYC", hint: "Identity and address proof" },
  { category: "bank_statement", label: "Bank statement", hint: "Last 3–6 months of inflows" },
  { category: "dealer_invoice", label: "Dealer invoice", hint: "Asset price and down payment" },
  { category: "platform_earnings", label: "Platform earnings", hint: "Gig platform payout history" },
];

export default function DocumentsPage({ params }: PageProps) {
  const { id } = use(params);
  const docs = useAsync(() => api.listDocuments(id), [id]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const onUploaded = (doc: Document) => {
    docs.setData((prev) => [...(prev ?? []), doc]);
  };

  const onDelete = async (doc: Document) => {
    if (!window.confirm(`Delete ${doc.file_name}?`)) return;
    setDeletingId(doc.id);
    setDeleteError(null);
    try {
      await api.deleteDocument(doc.id);
      docs.setData((prev) => (prev ?? []).filter((d) => d.id !== doc.id));
    } catch (err) {
      setDeleteError(errorMessage(err));
    } finally {
      setDeletingId(null);
    }
  };

  const uploadedCategories = useMemo(() => {
    const set = new Set<string>();
    for (const d of docs.data ?? []) if (d.category) set.add(d.category);
    return set;
  }, [docs.data]);
  const coveredCount = EXPECTED.filter((e) => uploadedCategories.has(e.category)).length;
  const total = docs.data?.length ?? 0;

  return (
    <ApplicationPageFrame
      applicationId={id}
      title="Documents"
      description="Upload the borrower's documents. Each file is parsed and a text preview is stored."
      actions={
        <Button asChild size="sm" variant="brand">
          <Link href={`/applications/${id}`}>
            Continue to underwriting <ArrowRight />
          </Link>
        </Button>
      }
    >
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Card className="animate-in-up">
            <CardHeader>
              <SectionHeading icon={<FileUp />} title="Upload" description="Select a category, then drop files or browse." />
            </CardHeader>
            <CardContent>
              <DocumentUploader applicationId={id} onUploaded={onUploaded} />
            </CardContent>
          </Card>

          <Card className="animate-in-up delay-1">
            <CardHeader>
              <SectionHeading
                icon={<ListChecks />}
                title="What to upload"
                description="The extraction agents look for these four categories."
                actions={
                  <span className="text-xs font-medium text-muted-foreground tnum">
                    {coveredCount}/{EXPECTED.length} covered
                  </span>
                }
              />
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Progress
                value={coveredCount / EXPECTED.length}
                tone={coveredCount === EXPECTED.length ? "good" : "neutral"}
                label="Categories covered"
                className="h-1.5"
              />
              <ul className="flex flex-col divide-y">
                {EXPECTED.map((e) => {
                  const done = uploadedCategories.has(e.category);
                  return (
                    <li key={e.category} className="flex items-center gap-3 py-2.5 first:pt-1 last:pb-1">
                      <span
                        className={cn(
                          "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition-colors",
                          done ? "border-success/40 bg-success-soft text-success" : "border-border bg-muted/50 text-muted-foreground/60"
                        )}
                        aria-hidden="true"
                      >
                        {done ? <Check className="h-3.5 w-3.5" strokeWidth={3} /> : <Circle className="h-2 w-2" />}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className={cn("text-sm font-medium", !done && "text-foreground/80")}>{e.label}</div>
                        <div className="text-xs text-muted-foreground">{e.hint}</div>
                      </div>
                      {done ? <Badge variant="success">Uploaded</Badge> : <Badge variant="muted">Missing</Badge>}
                    </li>
                  );
                })}
              </ul>
            </CardContent>
          </Card>
        </div>

        <Card className="animate-in-up delay-2 lg:col-span-3">
          <CardHeader>
            <SectionHeading
              icon={<Files />}
              title={
                <span className="inline-flex items-center gap-2">
                  Uploaded documents
                  {docs.data ? <Badge variant="secondary" className="tnum">{total}</Badge> : null}
                </span>
              }
              description="Expand a document to see the extracted text preview."
            />
          </CardHeader>
          <CardContent>
            {docs.error ? (
              <Alert variant="destructive" title="Could not load documents" className="mb-3">
                {docs.error}
              </Alert>
            ) : null}
            {deleteError ? (
              <Alert variant="destructive" title="Delete failed" className="mb-3">
                {deleteError}
              </Alert>
            ) : null}
            {docs.loading && !docs.data ? (
              <SkeletonBlock lines={4} />
            ) : (
              <DocumentList documents={docs.data ?? []} onDelete={onDelete} deletingId={deletingId} />
            )}
          </CardContent>
        </Card>
      </div>
    </ApplicationPageFrame>
  );
}
