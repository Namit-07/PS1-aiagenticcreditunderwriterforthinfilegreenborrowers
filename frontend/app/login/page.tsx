"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Check, Leaf, LogIn } from "lucide-react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api, errorMessage } from "@/lib/api";
import { getToken, setSession } from "@/lib/session";
import { loginSchema, zodErrors } from "@/lib/validations";

const POINTS = [
  "Facts with confidence scores and citations",
  "Human review whenever the evidence is weak",
  "Deterministic EMI · FOIR · LTV, versioned policies",
  "Replayable audit trail and exportable credit memo",
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (getToken()) router.replace("/dashboard");
  }, [router]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = loginSchema.safeParse({ email, password });
    if (!parsed.success) {
      setErrors(zodErrors(parsed.error));
      return;
    }
    setErrors({});
    setSubmitting(true);
    try {
      const res = await api.login(parsed.data.email, parsed.data.password);
      setSession(res.access_token, res.user ?? { email: parsed.data.email, name: "", role: "" });
      router.replace("/dashboard");
    } catch (err) {
      setApiError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="grid min-h-screen bg-background lg:grid-cols-[1.05fr_1fr]">
      {/* brand panel */}
      <section className="relative hidden overflow-hidden bg-sidebar p-10 text-sidebar-foreground lg:flex lg:flex-col">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.12]"
          style={{
            backgroundImage: "radial-gradient(hsl(150 40% 70%) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
          }}
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-32 -left-32 h-[460px] w-[460px] rounded-full opacity-40 blur-3xl"
          style={{ background: "radial-gradient(closest-side, hsl(158 55% 30%), transparent)" }}
          aria-hidden="true"
        />
        <Link href="/" className="relative flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-gradient text-white shadow-glow">
            <Leaf className="h-[18px] w-[18px]" />
          </span>
          <span className="leading-tight">
            <span className="block text-[15px] font-bold tracking-tight text-white">Verdant</span>
            <span className="block text-[11px] text-sidebar-muted">AI Credit Underwriter</span>
          </span>
        </Link>

        <div className="relative my-auto max-w-md">
          <h1 className="text-3xl font-bold leading-tight tracking-tight text-white xl:text-4xl">
            Credit decisions you can <span className="text-brand-gradient">show your working for.</span>
          </h1>
          <p className="mt-4 text-[15px] leading-relaxed text-sidebar-foreground/85">
            An underwriting workspace for gig-economy and EV borrowers with no credit file. Documents in, evidence out,
            policy applied, human where it matters.
          </p>
          <ul className="mt-8 space-y-3">
            {POINTS.map((p) => (
              <li key={p} className="flex items-start gap-3 text-sm">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success/20 text-[hsl(152_60%_70%)]">
                  <Check className="h-3 w-3" />
                </span>
                <span className="text-sidebar-foreground">{p}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative text-xs text-sidebar-muted">Deterministic financials · versioned policy · full audit trail</div>
      </section>

      {/* form panel */}
      <section className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm animate-in-up">
          <Link href="/" className="mb-8 inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground lg:hidden">
            <ArrowLeft className="h-3.5 w-3.5" /> Back to home
          </Link>
          <div className="mb-6 flex items-center gap-3 lg:hidden">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-gradient text-white shadow-glow">
              <Leaf className="h-[18px] w-[18px]" />
            </span>
            <span className="text-[15px] font-bold tracking-tight">Verdant</span>
          </div>

          <div className="eyebrow">Welcome back</div>
          <h2 className="mt-1.5 text-2xl font-bold tracking-tight">Sign in to the underwriter</h2>
          <p className="mt-1.5 text-sm text-muted-foreground">Demo auth: any email and password are accepted.</p>

          <form onSubmit={onSubmit} className="mt-8 flex flex-col gap-4" noValidate>
            <Field label="Work email" htmlFor="email" error={errors.email}>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="analyst@lender.example"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <Field label="Password" htmlFor="password" error={errors.password}>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
            {apiError ? <Alert variant="destructive">{apiError}</Alert> : null}
            <Button type="submit" disabled={submitting} size="lg" variant="brand" className="mt-2 w-full">
              <LogIn />
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            By continuing you agree this is a hackathon demo running on synthetic data.
          </p>
        </div>
      </section>
    </main>
  );
}
