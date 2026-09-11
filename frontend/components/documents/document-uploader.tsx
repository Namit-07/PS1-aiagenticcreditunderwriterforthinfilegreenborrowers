"use client";

import { useRef, useState, type DragEvent } from "react";
import { FileImage, FileText, FileType, FileUp, Loader2, Upload, X } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";
import type { Document } from "@/lib/types";
import { cn, formatBytes, humanize } from "@/lib/utils";
import { DOCUMENT_CATEGORIES } from "@/lib/validations";

const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED_EXT = ["pdf", "png", "jpg", "jpeg", "txt"];
const ALLOWED_MIME = ["application/pdf", "image/png", "image/jpeg", "text/plain"];

function validateFile(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  const typeOk = ALLOWED_EXT.includes(ext) || ALLOWED_MIME.includes(file.type);
  if (!typeOk) return `${file.name}: unsupported type (allowed: pdf, png, jpg, jpeg, txt)`;
  if (file.size > MAX_BYTES) return `${file.name}: exceeds 10 MB (${formatBytes(file.size)})`;
  return null;
}

function FileIcon({ name, type, className }: { name: string; type?: string | null; className?: string }) {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (type?.startsWith("image/") || ["png", "jpg", "jpeg"].includes(ext)) return <FileImage className={className} />;
  if (type === "text/plain" || ext === "txt") return <FileType className={className} />;
  return <FileText className={className} />;
}

interface Pending {
  file: File;
  error: string | null;
}

export function DocumentUploader({
  applicationId,
  onUploaded,
}: {
  applicationId: string;
  onUploaded: (doc: Document) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [category, setCategory] = useState<string>("bank_statement");
  const [pending, setPending] = useState<Pending[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [errors, setErrors] = useState<string[]>([]);

  const addFiles = (files: FileList | File[]) => {
    const next: Pending[] = Array.from(files).map((file) => ({ file, error: validateFile(file) }));
    setPending((p) => [...p, ...next]);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  };

  const upload = async () => {
    const valid = pending.filter((p) => !p.error);
    if (valid.length === 0) return;
    setUploading(true);
    setErrors([]);
    const failed: string[] = [];
    for (let i = 0; i < valid.length; i++) {
      const { file } = valid[i];
      setProgress(`Uploading ${i + 1}/${valid.length}: ${file.name}`);
      try {
        const doc = await api.uploadDocument(applicationId, file, category);
        onUploaded(doc);
      } catch (err) {
        failed.push(`${file.name}: ${errorMessage(err)}`);
      }
    }
    setProgress(null);
    setUploading(false);
    setErrors(failed);
    setPending((p) => p.filter((x) => x.error || failed.some((f) => f.startsWith(`${x.file.name}:`))));
  };

  const validCount = pending.filter((p) => !p.error).length;
  const invalidCount = pending.length - validCount;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1.5">
        <div className="flex items-baseline justify-between gap-2">
          <Label htmlFor="doc_category">Category</Label>
          <span className="text-[11px] text-muted-foreground">applies to every file in this batch</span>
        </div>
        <Select id="doc_category" value={category} onChange={(e) => setCategory(e.target.value)}>
          {DOCUMENT_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {humanize(c)}
            </option>
          ))}
        </Select>
      </div>

      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        aria-label="Drop files here or click to browse"
        className={cn(
          "bg-grid group relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30",
          dragging
            ? "border-primary bg-primary-soft/60 shadow-glow"
            : "border-border bg-muted/30 hover:border-primary/50 hover:bg-primary-soft/30"
        )}
      >
        <div
          className={cn(
            "flex h-14 w-14 items-center justify-center rounded-xl bg-primary-soft text-primary shadow-sm ring-1 ring-primary/10 transition-transform duration-200",
            dragging ? "scale-110" : "group-hover:-translate-y-0.5"
          )}
        >
          <FileUp className="h-6 w-6" />
        </div>
        <div>
          <div className="text-sm font-semibold">{dragging ? "Release to add files" : "Drop files here or click to browse"}</div>
          <div className="mt-1 text-xs text-muted-foreground">PDF, PNG, JPG, JPEG or TXT · max 10 MB each</div>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-1.5">
          {["PDF", "PNG", "JPG", "TXT"].map((t) => (
            <span key={t} className="rounded-md border bg-card px-1.5 py-0.5 font-mono text-[10px] font-medium text-muted-foreground">
              {t}
            </span>
          ))}
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.txt,application/pdf,image/png,image/jpeg,text/plain"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {pending.length > 0 ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="eyebrow">
              Ready to upload · {validCount}
              {invalidCount ? ` · ${invalidCount} skipped` : ""}
            </span>
            <button
              type="button"
              className="text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground"
              onClick={() => setPending([])}
              disabled={uploading}
            >
              Clear all
            </button>
          </div>
          <ul className="flex flex-col gap-1.5">
            {pending.map((p, i) => (
              <li
                key={`${p.file.name}-${i}`}
                className={cn(
                  "flex items-center gap-3 rounded-md border bg-card px-3 py-2 text-sm shadow-sm transition-colors",
                  p.error ? "border-danger/40 bg-danger-soft/40" : "hover:border-primary/30"
                )}
              >
                <span
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-md [&_svg]:h-4 [&_svg]:w-4",
                    p.error ? "bg-danger-soft text-danger" : "bg-primary-soft text-primary"
                  )}
                >
                  <FileIcon name={p.file.name} type={p.file.type} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{p.file.name}</div>
                  <div className={cn("truncate text-xs", p.error ? "text-danger" : "text-muted-foreground")}>
                    {p.error ?? `${formatBytes(p.file.size)} · ${humanize(category)}`}
                  </div>
                </div>
                <button
                  type="button"
                  aria-label={`Remove ${p.file.name}`}
                  className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
                  onClick={() => setPending((list) => list.filter((_, j) => j !== i))}
                  disabled={uploading}
                >
                  <X className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {errors.length > 0 ? (
        <Alert variant="destructive" title="Some uploads failed">
          <ul className="list-disc pl-4">
            {errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center gap-3 border-t pt-4">
        <Button variant="brand" onClick={upload} disabled={uploading || validCount === 0}>
          {uploading ? <Loader2 className="animate-spin" /> : <Upload />}
          {uploading ? "Uploading…" : `Upload ${validCount || ""} file${validCount === 1 ? "" : "s"}`}
        </Button>
        {progress ? (
          <span className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-info pulse-ring" aria-hidden="true" />
            <span className="truncate tnum">{progress}</span>
          </span>
        ) : validCount === 0 ? (
          <span className="text-xs text-muted-foreground">Add at least one file to enable upload.</span>
        ) : null}
      </div>
    </div>
  );
}
