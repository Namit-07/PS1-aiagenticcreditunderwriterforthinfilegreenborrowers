"use client";

import { Cpu, KeyRound, RefreshCw, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/use-async";
import { api } from "@/lib/api";

/** Live status of the language-model provider (Gemini free tier / OpenAI / template). */
export function AiProviderCard() {
  const health = useAsync(() => api.health(), []);
  const ai = health.data?.ai_service;
  const provider = ai?.llm_provider ?? (ai?.mock_ai_mode === false ? "configured" : "mock");
  const live = provider !== "mock" && provider !== "configured";

  return (
    <Card>
      <CardHeader>
        <SectionHeading
          icon={<Sparkles />}
          title="Language model"
          description="Writes the credit-memo narrative and risk reasoning. It never computes EMI, FOIR or LTV — those stay deterministic."
          actions={
            <Button variant="outline" size="sm" onClick={health.reload} disabled={health.loading}>
              <RefreshCw className={health.loading ? "animate-spin" : undefined} /> Refresh
            </Button>
          }
        />
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-[1fr_1.2fr]">
        <div className="flex flex-col gap-3 rounded-md border bg-muted/40 p-4">
          {health.loading && !health.data ? (
            <Skeleton className="h-10" />
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary-soft text-primary">
                  <Cpu className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-semibold capitalize">{live ? provider : "Template mode (₹0)"}</div>
                  <div className="text-xs text-muted-foreground">
                    {live ? `model ${ai?.llm_model ?? "—"}` : "No API key configured — deterministic template narrative"}
                  </div>
                </div>
                <Badge variant={live ? "success" : "muted"} dot className="ml-auto">
                  {health.error ? "unreachable" : live ? "live" : "offline"}
                </Badge>
              </div>
              <dl className="grid grid-cols-2 gap-y-1 text-xs">
                <dt className="text-muted-foreground">AI service</dt>
                <dd className="text-right font-medium">{ai?.status ?? health.error ?? "—"}</dd>
                <dt className="text-muted-foreground">Risk backend</dt>
                <dd className="text-right font-medium">{ai?.risk_backend ?? "—"}</dd>
                <dt className="text-muted-foreground">Graph backend</dt>
                <dd className="text-right font-medium">{ai?.graph_backend ?? "—"}</dd>
              </dl>
            </>
          )}
        </div>
        <div className="flex flex-col gap-2 text-[13px] leading-relaxed text-muted-foreground">
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <KeyRound className="h-4 w-4 text-primary" /> Enable Gemini (free tier)
          </div>
          <ol className="list-decimal space-y-1 pl-5">
            <li>
              Create a free key at <span className="font-mono text-xs">aistudio.google.com/apikey</span>.
            </li>
            <li>
              Put it in <span className="font-mono text-xs">ai-service/.env</span> as{" "}
              <span className="font-mono text-xs">GEMINI_API_KEY=…</span> (see <span className="font-mono text-xs">.env.example</span>).
            </li>
            <li>Restart the AI service. Runs completed afterwards get a Gemini-written executive summary and borrower explanation.</li>
          </ol>
          <p className="text-xs">
            Rate limits (HTTP 429) or any model error fall back to the template automatically, so underwriting never blocks on the model.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
