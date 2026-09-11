import { Activity } from "lucide-react";

import { RiskBandBadge } from "@/components/applications/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RingMeter } from "@/components/ui/ring-meter";
import type { Risk } from "@/lib/types";
import { cn, formatNumber, humanize } from "@/lib/utils";

const TONE: Record<Risk["risk_band"], "good" | "warn" | "bad"> = { LOW: "good", MEDIUM: "warn", HIGH: "bad" };
const TEXT: Record<Risk["risk_band"], string> = { LOW: "text-success", MEDIUM: "text-warning", HIGH: "text-danger" };

export function RiskCard({ risk }: { risk: Risk | null }) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
            <Activity className="h-4 w-4" />
          </span>
          <div>
            <CardTitle>Risk signal</CardTitle>
            <CardDescription className="mt-0.5">
              {risk ? (
                <>
                  <span className="font-mono text-xs">{risk.model_backend}</span> · model {risk.model_version}
                </>
              ) : (
                "Not scored."
              )}
            </CardDescription>
          </div>
        </div>
        {risk ? <RiskBandBadge band={risk.risk_band} /> : null}
      </CardHeader>
      {risk ? (
        <CardContent className="flex flex-col gap-5">
          <div className="flex items-center gap-5">
            <RingMeter
              value={risk.risk_score}
              tone={TONE[risk.risk_band] ?? "neutral"}
              size={96}
              stroke={9}
              label={risk.risk_score.toFixed(2)}
              sublabel="score"
            />
            <div className="min-w-0">
              <div className="eyebrow">Risk band</div>
              <div className={cn("mt-0.5 text-2xl font-bold leading-none tracking-tight", TEXT[risk.risk_band] ?? "text-foreground")}>
                {risk.risk_band}
              </div>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                Score <span className="font-medium text-foreground tnum">{risk.risk_score.toFixed(3)}</span> on a 0–1 scale, where 0 is
                safest and 1 is riskiest.
              </p>
            </div>
          </div>
          {risk.features && Object.keys(risk.features).length > 0 ? (
            <div>
              <div className="eyebrow mb-2">Model features</div>
              <dl className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
                {Object.entries(risk.features).map(([k, v]) => (
                  <div key={k} className="flex min-w-0 flex-col rounded-md bg-muted/50 px-2.5 py-1.5">
                    <dt className="truncate text-[10px] font-medium uppercase tracking-wide text-muted-foreground" title={k}>
                      {humanize(k)}
                    </dt>
                    <dd className="text-[13px] font-semibold tnum">{formatNumber(v, 3)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : null}
        </CardContent>
      ) : null}
    </Card>
  );
}
