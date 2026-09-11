"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Play } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";
import type { PolicyProfile } from "@/lib/types";
import { POLICY_PROFILES } from "@/lib/validations";
import { humanize } from "@/lib/utils";

export function StartUnderwriting({ applicationId, disabled }: { applicationId: string; disabled?: boolean }) {
  const router = useRouter();
  const [profile, setProfile] = useState<PolicyProfile>("default");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.startUnderwrite(applicationId, profile);
      router.push(`/applications/${applicationId}/underwriting?run=${encodeURIComponent(res.run_id)}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="policy_profile" className="eyebrow">
          Policy profile
        </Label>
        <Select
          id="policy_profile"
          value={profile}
          onChange={(e) => setProfile(e.target.value as PolicyProfile)}
          disabled={busy}
        >
          {POLICY_PROFILES.map((p) => (
            <option key={p} value={p}>
              {humanize(p)}
            </option>
          ))}
        </Select>
      </div>
      <Button variant="brand" size="lg" className="w-full" onClick={start} disabled={busy || disabled}>
        {busy ? <Loader2 className="animate-spin" /> : <Play />}
        {busy ? "Starting run…" : "Start underwriting"}
      </Button>
      {error ? (
        <Alert variant="destructive" title="Could not start the run">
          {error}
        </Alert>
      ) : null}
    </div>
  );
}
