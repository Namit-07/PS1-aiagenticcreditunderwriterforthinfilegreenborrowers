"use client";

import { useEffect, useState } from "react";
import { Activity, BrainCircuit } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { PageHeader } from "@/components/layout/page-header";
import { RiskMetricsPanel } from "@/components/risk/risk-metrics-panel";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SectionHeading } from "@/components/ui/section-heading";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { api, errorMessage } from "@/lib/api";
import type { RiskMetrics } from "@/lib/types";

export default function RiskModelPage() {
  const [metrics, setMetrics] = useState<RiskMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load(th = 0.5, n = 800) {
    setLoading(true);
    setError(null);
    try {
      setMetrics(await api.riskMetrics(th, n));
    } catch (err) {
      setError(errorMessage(err));
      setMetrics(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppShell>
      <PageHeader
        eyebrow="Machine learning"
        title="Risk model evaluation"
        description="Offline metrics for the XGBoost risk signal (confusion matrix, accuracy, precision, recall/sensitivity, specificity, F1, AUC). Trained on synthetic data only — a supporting signal, never the final decision."
        actions={
          <Button variant="outline" size="sm" onClick={() => load()}>
            <Activity /> Refresh
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <SectionHeading
            icon={<BrainCircuit />}
            title="Evaluation scores"
            description="Positive class = risky borrower at the chosen score threshold (0.50 = elevated/high risk)."
          />
        </CardHeader>
        <CardContent>
          {error ? (
            <Alert variant="destructive" title="Could not load metrics">
              {error}
            </Alert>
          ) : loading ? (
            <div className="rounded-md border bg-muted/40 p-6 text-sm text-muted-foreground">
              Evaluating the risk model on synthetic data…
            </div>
          ) : (
            <RiskMetricsPanel metrics={metrics} />
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}