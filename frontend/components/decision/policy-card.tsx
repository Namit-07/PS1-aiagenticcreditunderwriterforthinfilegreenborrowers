import { ScrollText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { JsonView } from "@/components/ui/json-view";
import type { PolicyInfo } from "@/lib/types";
import { displayValue, humanize } from "@/lib/utils";

function isPrimitive(v: unknown): v is string | number | boolean | null {
  return v === null || ["string", "number", "boolean"].includes(typeof v);
}

/** Policy profile, version and the limits found in policy.config. */
export function PolicyCard({ policy }: { policy: PolicyInfo | null | undefined }) {
  const config = policy?.config ?? {};
  const entries = Object.entries(config);
  const simple = entries.filter(([, v]) => isPrimitive(v));
  const complex = entries.filter(([, v]) => !isPrimitive(v));

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
            <ScrollText className="h-4 w-4" />
          </span>
          <div>
            <CardTitle>Policy</CardTitle>
            <CardDescription className="mt-0.5">
              Rules applied by the <span className="font-mono text-xs">decision_policy</span> node.
            </CardDescription>
          </div>
        </div>
        {policy ? (
          <div className="flex flex-wrap justify-end gap-1.5">
            <Badge variant="brand">{humanize(policy.profile)}</Badge>
            <Badge variant="outline" className="font-mono">
              v{policy.version}
            </Badge>
          </div>
        ) : null}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {simple.length > 0 ? (
          <div>
            <div className="eyebrow mb-2">Limits</div>
            <dl className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {simple.map(([k, v]) => (
                <div key={k} className="flex items-center justify-between gap-3 rounded-md bg-muted/50 px-2.5 py-1.5 text-[13px]">
                  <dt className="truncate text-muted-foreground" title={k}>
                    {humanize(k)}
                  </dt>
                  <dd className="shrink-0 font-semibold tnum">{displayValue(v)}</dd>
                </div>
              ))}
            </dl>
          </div>
        ) : (
          <p className="rounded-md border border-dashed px-3 py-4 text-center text-sm text-muted-foreground">
            No limits reported in policy.config.
          </p>
        )}
        {complex.length > 0 ? (
          <JsonView value={Object.fromEntries(complex)} collapsible="Show nested config" />
        ) : null}
      </CardContent>
    </Card>
  );
}
