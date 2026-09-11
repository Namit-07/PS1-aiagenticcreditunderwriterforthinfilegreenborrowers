/** Browser-side session storage for the demo auth token. */

import type { AuthUser } from "@/lib/types";

export const TOKEN_KEY = "acu_token";
export const USER_KEY = "acu_user";

function safeGet(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    // ignore storage failures (private mode etc.)
  }
}

export function getToken(): string | null {
  return safeGet(TOKEN_KEY);
}

export function getUser(): AuthUser | null {
  const raw = safeGet(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setSession(token: string, user: AuthUser | null) {
  safeSet(TOKEN_KEY, token);
  safeSet(USER_KEY, user ? JSON.stringify(user) : null);
}

export function clearSession() {
  safeSet(TOKEN_KEY, null);
  safeSet(USER_KEY, null);
}
