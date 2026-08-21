"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LiveDemoView } from "@/components/LiveDemoView";
import { DiscussionGuide } from "@/components/DiscussionGuide";
import { TabBar, type AppTab } from "@/components/TabBar";

export default function Home() {
  const [tab, setTab] = useState<AppTab>("demo");
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", width: "100%", overflow: "hidden" }}>
      <TabBar active={tab} onChange={setTab} onLogout={handleLogout} />
      <div style={{ flex: 1, minHeight: 0 }}>
        <div style={{ display: tab === "demo" ? "contents" : "none" }}>
          <LiveDemoView />
        </div>
        <div style={{ display: tab === "guide" ? "contents" : "none" }}>
          <DiscussionGuide />
        </div>
      </div>
    </div>
  );
}
