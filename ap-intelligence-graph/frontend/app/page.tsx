"use client";

import { useState } from "react";
import { LiveDemoView } from "@/components/LiveDemoView";
import { DiscussionGuide } from "@/components/DiscussionGuide";
import { TabBar, type AppTab } from "@/components/TabBar";

/**
 * Top-level tab shell. Both views are mounted for the app's entire lifetime;
 * only `display` toggles between them (`display: contents` on the active
 * wrapper so it doesn't affect LiveDemoView's own flex/height layout, `none`
 * on the inactive one). This is deliberate: LiveDemoView owns a lot of
 * component state (chat transcript, decisions, graph selection/zoom/drag,
 * panel sizing) plus DOM-only state (scroll positions) that a conditional
 * `{tab === "demo" && <LiveDemoView />}` would destroy by unmounting it on
 * every switch to the Discussion Guide. Neither view fetches anything or
 * talks to the backend as a result of the tab switch itself - LiveDemoView
 * only ever fetches from its own mount effect, which only runs once.
 */
export default function Home() {
  const [tab, setTab] = useState<AppTab>("demo");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", width: "100%", overflow: "hidden" }}>
      <TabBar active={tab} onChange={setTab} />
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
