"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { api, errorMessage } from "@/lib/api";
import type { Application, RunState } from "@/lib/types";
import { useAsync } from "@/hooks/use-async";

/**
 * Resolves the run id for an application page: `?run=` search param first,
 * falling back to `application.latest_run_id`.
 */
export function useRunId(applicationId: string) {
  const searchParams = useSearchParams();
  const paramRun = searchParams.get("run");
  const app = useAsync<Application>(() => api.getApplication(applicationId), [applicationId]);
  const runId = paramRun ?? app.data?.latest_run_id ?? null;
  return {
    runId,
    application: app.data,
    loading: app.loading,
    error: app.error,
    reloadApplication: app.reload,
  };
}

export const POLL_INTERVAL_MS = 1500;

/** Loads a run state and (optionally) polls while it is running. */
export function useRunState(runId: string | null, poll = false) {
  const [state, setState] = useState<RunState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(runId));
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!runId) {
      setState(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    setLoading(true);

    const fetchOnce = async () => {
      try {
        const next = await api.getRun(runId);
        if (cancelled) return;
        setState(next);
        setError(null);
        setLoading(false);
        if (poll && (next.status === "running" || next.status === "created")) {
          timer = setTimeout(fetchOnce, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (cancelled) return;
        setError(errorMessage(err));
        setLoading(false);
        // A transient failure (backend restart, 5xx) must not freeze a live run: keep polling.
        if (poll) timer = setTimeout(fetchOnce, POLL_INTERVAL_MS * 2);
      }
    };
    void fetchOnce();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [runId, poll, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);

  return { state, setState, error, loading, reload };
}
