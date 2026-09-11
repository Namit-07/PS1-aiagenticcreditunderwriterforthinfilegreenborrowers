/** Auth helpers (Team A).
 *
 * The app uses the backend demo auth (`POST /auth/login`, token in localStorage,
 * see `lib/session.ts`). Supabase helpers are kept for optional future use and are
 * guarded so that missing env vars never crash the app.
 */

import { createBrowserClient, createServerClient } from "@supabase/ssr";

import { BASE_URL } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { Application, DashboardStats } from "@/lib/types";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export function isSupabaseConfigured(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
}

export function getSupabaseClient() {
  if (!isSupabaseConfigured()) return null;
  return createBrowserClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}

export function getSupabaseServerClient() {
  if (!isSupabaseConfigured()) return null;
  return createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll: () => [],
      setAll: () => {},
    },
  });
}

export function buildUrl(path: string): string {
  return `${BASE_URL}${path}`;
}

export async function fetchWithAuth(
  path: string,
  token: string,
  init?: RequestInit & { headers?: Record<string, string> }
) {
  return fetch(buildUrl(path), {
    ...init,
    headers: { Authorization: `Bearer ${token}`, ...(init?.headers ?? {}) },
  });
}

/** Returns the demo token, falling back to a Supabase session if configured. */
export async function getAuthToken(): Promise<string | null> {
  const local = getToken();
  if (local) return local;
  const client = getSupabaseClient();
  if (!client) return null;
  try {
    const { data } = await client.auth.getSession();
    return data.session?.access_token ?? null;
  } catch {
    return null;
  }
}

export async function postApplication(token: string, payload: unknown): Promise<Response> {
  return fetchWithAuth("/applications", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export type { Application, DashboardStats };
