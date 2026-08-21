"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { TEXT } from "@/lib/design";

export function ResetDemoButton({ onReset }: { onReset: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConfirm() {
    setResetting(true);
    setError(null);
    try {
      await api.resetDemo();
      setConfirming(false);
      onReset();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setResetting(false);
    }
  }

  if (confirming) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12 }}>
        <span style={{ color: "#c9975a" }}>Reset all demo data?</span>
        <button
          onClick={handleConfirm}
          disabled={resetting}
          style={{ fontSize: 12, fontWeight: 600, color: "#c9975a", background: "transparent", border: "none", padding: "4px 2px", cursor: "pointer", opacity: resetting ? 0.5 : 1 }}
        >
          {resetting ? "Resetting…" : "Yes, reset"}
        </button>
        <button
          onClick={() => setConfirming(false)}
          disabled={resetting}
          style={{ fontSize: 12, color: TEXT.faint, background: "transparent", border: "none", padding: "4px 2px", cursor: "pointer", opacity: resetting ? 0.5 : 1 }}
        >
          Cancel
        </button>
        {error && <span style={{ color: "#c9975a" }}>{error}</span>}
      </div>
    );
  }

  return (
    <button
      onClick={() => setConfirming(true)}
      title="Demo-only: restores all data to the original seeded state. Not a production pattern."
      style={{ fontSize: 13, color: TEXT.secondary, background: "transparent", border: "none", padding: "6px 4px", cursor: "pointer", whiteSpace: "nowrap" }}
    >
      Reset
    </button>
  );
}
