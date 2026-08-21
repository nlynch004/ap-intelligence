"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ACCENT, SURFACE, TEXT } from "@/lib/design";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        setError(data.error || "Incorrect password.");
        return;
      }
      router.replace(params.get("from") || "/");
      router.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: SURFACE.app }}>
      <form
        onSubmit={submit}
        style={{
          width: 340, background: SURFACE.panel, border: `1px solid ${SURFACE.separator}`,
          borderRadius: 12, padding: 28, display: "flex", flexDirection: "column", gap: 14,
        }}
      >
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: TEXT.primary }}>AP Intelligence</div>
          <div style={{ fontSize: 13, color: TEXT.faint, marginTop: 2 }}>Admin access required.</div>
        </div>
        <input
          type="password"
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          style={{
            fontSize: 14, borderRadius: 8, border: `1px solid ${SURFACE.separator}`, background: SURFACE.raised,
            color: TEXT.primary, padding: "10px 12px", outline: "none",
          }}
        />
        {error && <div style={{ fontSize: 12.5, color: "#c9707a" }}>{error}</div>}
        <button
          type="submit"
          disabled={submitting || !password}
          style={{
            fontSize: 13.5, fontWeight: 600, padding: "10px 14px", borderRadius: 8, border: "none",
            background: ACCENT.blue, color: "#0a1622", cursor: "pointer", opacity: submitting || !password ? 0.5 : 1,
          }}
        >
          {submitting ? "Checking…" : "Log in"}
        </button>
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
