import { Badge, type BadgeVariant } from "@/components/ui/badge";
import type { ReasonSeverity, ReconciliationSeverity, ReviewStatus, RiskBand } from "@/lib/types";
import { humanize } from "@/lib/utils";

/*
  Outcome colours are reserved: approved = success, declined = danger,
  referred = warning, human_review / running = info. Status-like badges carry a
  leading dot so they read as state (not decoration) even at a glance.
*/

const APP_STATUS: Record<string, BadgeVariant> = {
  draft: "muted",
  documents_pending: "secondary",
  underwriting: "info",
  awaiting_human: "warning",
  decision_pending: "info",
  approved: "success",
  declined: "danger",
  referred: "warning",
  cancelled: "muted",
};

export function ApplicationStatusBadge({ status }: { status: string | null | undefined }) {
  if (!status) return <Badge variant="muted">—</Badge>;
  return (
    <Badge variant={APP_STATUS[status] ?? "secondary"} dot>
      {humanize(status)}
    </Badge>
  );
}

const DECISION: Record<string, BadgeVariant> = {
  approved: "success",
  declined: "danger",
  referred: "warning",
  human_review: "info",
};

export function DecisionBadge({
  decision,
  className,
}: {
  decision: string | null | undefined;
  className?: string;
}) {
  if (!decision) return <Badge variant="muted" className={className}>No decision</Badge>;
  return (
    <Badge variant={DECISION[decision] ?? "secondary"} className={className} dot>
      {humanize(decision)}
    </Badge>
  );
}

const RUN_STATUS: Record<string, BadgeVariant> = {
  created: "muted",
  running: "info",
  awaiting_human: "warning",
  completed: "success",
  failed: "danger",
};

export function RunStatusBadge({ status }: { status: string | null | undefined }) {
  if (!status) return <Badge variant="muted">—</Badge>;
  return (
    <Badge variant={RUN_STATUS[status] ?? "secondary"} dot>
      {humanize(status)}
    </Badge>
  );
}

const SEVERITY: Record<ReasonSeverity, BadgeVariant> = {
  info: "info",
  warning: "warning",
  blocker: "danger",
};

export function SeverityBadge({ severity }: { severity: ReasonSeverity | string }) {
  return (
    <Badge variant={SEVERITY[severity as ReasonSeverity] ?? "secondary"}>{humanize(severity)}</Badge>
  );
}

const RECON_SEVERITY: Record<ReconciliationSeverity, BadgeVariant> = {
  LOW: "info",
  MEDIUM: "warning",
  HIGH: "danger",
};

export function ReconSeverityBadge({ severity }: { severity: ReconciliationSeverity | string }) {
  return (
    <Badge variant={RECON_SEVERITY[severity as ReconciliationSeverity] ?? "secondary"}>{severity}</Badge>
  );
}

const RISK_BAND: Record<RiskBand, BadgeVariant> = {
  LOW: "success",
  MEDIUM: "warning",
  HIGH: "danger",
};

export function RiskBandBadge({ band }: { band: RiskBand | string | null | undefined }) {
  if (!band) return <Badge variant="muted">—</Badge>;
  return <Badge variant={RISK_BAND[band as RiskBand] ?? "secondary"}>{band} risk</Badge>;
}

const REVIEW_STATUS: Record<ReviewStatus, BadgeVariant> = {
  auto: "muted",
  accepted: "success",
  corrected: "info",
  rejected: "danger",
};

export function ReviewStatusBadge({ status }: { status: ReviewStatus | string | null | undefined }) {
  const s = status ?? "auto";
  return <Badge variant={REVIEW_STATUS[s as ReviewStatus] ?? "secondary"}>{humanize(s)}</Badge>;
}
