"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, FileImage, FileText, FileType, Files, Trash2 } from "lucide-react";

import { Badge, type BadgeVariant } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import type { Document } from "@/lib/types";
import { cn, formatBytes, formatDateTime, humanize } from "@/lib/utils";

const STAGGER = ["", "delay-1", "delay-2", "delay-3", "delay-4"];

const CATEGORY_VARIANT: Record<string, BadgeVariant> = {
  kyc: "brand",
  bank_statement: "brand",
  dealer_invoice: "brand",
  platform_earnings: "brand",
  other: "muted",
};

function fileKind(d: Document): { icon: React.ReactNode; label: string } {
  const ext = d.file_name.split(".").pop()?.toLowerCase() ?? "";
  const type = d.content_type ?? "";
  if (type.startsWith("image/") || ["png", "jpg", "jpeg"].includes(ext)) {
    return { icon: <FileImage />, label: ext ? ext.toUpperCase() : "IMAGE" };
  }
  if (type === "text/plain" || ext === "txt") return { icon: <FileType />, label: "TXT" };
  if (type === "application/pdf" || ext === "pdf") return { icon: <FileText />, label: "PDF" };
  return { icon: <FileText />, label: ext ? ext.toUpperCase() : "FILE" };
}

export function DocumentList({
  documents,
  onDelete,
  deletingId,
}: {
  documents: Document[];
  onDelete: (doc: Document) => void;
  deletingId: string | null;
}) {
  const [open, setOpen] = useState<Record<string, boolean>>({});

  if (documents.length === 0) {
    return (
      <EmptyState
        icon={<Files />}
        title="No documents uploaded"
        description="Upload KYC, bank statements, dealer invoices or platform earnings. Each file is parsed and a text preview is stored."
      />
    );
  }

  return (
    <ul className="flex flex-col gap-2.5">
      {documents.map((d, i) => {
        const expanded = Boolean(open[d.id]);
        const deleting = deletingId === d.id;
        const kind = fileKind(d);
        const category = d.category ?? "other";
        return (
          <li
            key={d.id}
            className={cn(
              "animate-in-up rounded-lg border bg-card shadow-card transition-colors",
              deleting && "opacity-60",
              STAGGER[i] ?? ""
            )}
          >
            <div className="flex items-start gap-3 p-3.5 sm:p-4">
              <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary [&_svg]:h-5 [&_svg]:w-5">
                {kind.icon}
                <span className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 rounded border bg-card px-1 font-mono text-[9px] font-semibold leading-[14px] text-muted-foreground">
                  {kind.label}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="truncate text-sm font-semibold" title={d.file_name}>
                    {d.file_name}
                  </span>
                  <Badge variant={CATEGORY_VARIANT[category] ?? "secondary"}>{humanize(category)}</Badge>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground">
                  <span className="tnum">{formatBytes(d.size_bytes)}</span>
                  <span aria-hidden="true">·</span>
                  <span className="tnum">{formatDateTime(d.uploaded_at)}</span>
                  {d.content_type ? (
                    <>
                      <span aria-hidden="true" className="hidden sm:inline">
                        ·
                      </span>
                      <span className="hidden font-mono text-[11px] sm:inline">{d.content_type}</span>
                    </>
                  ) : null}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-0.5">
                {d.text_preview ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setOpen((o) => ({ ...o, [d.id]: !expanded }))}
                    aria-expanded={expanded}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    {expanded ? <ChevronDown /> : <ChevronRight />}
                    <span className="hidden sm:inline">Preview</span>
                  </Button>
                ) : null}
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="text-muted-foreground hover:bg-danger-soft hover:text-danger"
                  onClick={() => onDelete(d)}
                  disabled={deleting}
                  aria-label={deleting ? `Deleting ${d.file_name}` : `Delete ${d.file_name}`}
                  title={deleting ? "Deleting…" : "Delete"}
                >
                  <Trash2 />
                </Button>
              </div>
            </div>
            {expanded && d.text_preview ? (
              <div className="border-t bg-muted/30 px-3.5 pb-3.5 pt-3 sm:px-4 sm:pb-4">
                <div className="mb-2 flex items-center justify-between">
                  <span className="eyebrow">Extracted text preview</span>
                  <span className="text-[11px] text-muted-foreground tnum">{d.text_preview.length.toLocaleString()} chars</span>
                </div>
                <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md border bg-[hsl(var(--sidebar))] p-3.5 font-mono text-[12px] leading-relaxed text-[hsl(var(--sidebar-foreground))]">
                  {d.text_preview}
                </pre>
              </div>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
