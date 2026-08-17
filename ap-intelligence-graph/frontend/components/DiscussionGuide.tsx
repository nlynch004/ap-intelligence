"use client";

import { useEffect, useRef, useState } from "react";
import { ACCENT, FONT_MONO, SURFACE, TEXT } from "@/lib/design";
import {
  DISCUSSION_GUIDE_HEADER,
  DISCUSSION_SECTIONS,
  PRODUCT_THESIS,
  type AdoptionSection,
  type ArchitectureChain,
  type ArchitectureSection,
  type BulletsSimpleSection,
  type DiscussionSection,
  type MeasurementSection,
  type PhasesSection,
  type RagCompareSection,
  type RankedRisk,
  type RankedRisksSection,
  type RealVsSimplifiedSection,
  type ResponsibilitiesSection,
  type TwoColumn,
} from "@/lib/discussionGuide";

// Static presenter content - see lib/discussionGuide.ts. This component
// renders it; it never fetches, never calls the backend, and never touches
// the live demo's graph/chat state. Mounted for the app's entire lifetime
// (app/page.tsx toggles visibility only), so its own state (which section is
// active in the nav) is cheap to lose and cheap to keep - it just doesn't
// matter for the "preserve demo state" requirement, which is about
// LiveDemoView, not this component.

function SectionEyebrow({ text }: { text: string }) {
  return <div style={{ fontSize: 11, letterSpacing: "0.08em", color: TEXT.faint, marginBottom: 10, textTransform: "uppercase" }}>{text}</div>;
}

function BulletList({ items, tone = "default" }: { items: string[]; tone?: "default" | "muted" }) {
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
      {items.map((item, i) => (
        <li key={i} style={{ display: "flex", gap: 10, fontSize: 13.5, lineHeight: 1.55, color: tone === "muted" ? TEXT.secondary2 : TEXT.strongSecondary2 }}>
          <span style={{ color: TEXT.faint2, flex: "none" }}>–</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function KeyLine({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        marginTop: 18,
        background: SURFACE.raised,
        borderLeft: `3px solid ${ACCENT.blue}`,
        borderRadius: "0 10px 10px 0",
        padding: "12px 16px",
        fontSize: 14,
        fontWeight: 600,
        color: TEXT.primary,
        lineHeight: 1.5,
      }}
    >
      {children}
    </div>
  );
}

function TwoColBlock({ left, right }: { left: TwoColumn; right: TwoColumn }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 24, marginTop: 14 }}>
      <div>
        <SectionEyebrow text={left.heading} />
        <BulletList items={left.bullets} />
      </div>
      <div>
        <SectionEyebrow text={right.heading} />
        <BulletList items={right.bullets} />
      </div>
    </div>
  );
}

function Chain({ steps }: { steps: string[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      {steps.map((step, i) => (
        <div key={step}>
          <div style={{ background: SURFACE.raised, border: `1px solid ${SURFACE.separator}`, borderRadius: 8, padding: "10px 14px", fontSize: 13, color: TEXT.strongSecondary2, textAlign: "center" }}>
            {step}
          </div>
          {i < steps.length - 1 && <div style={{ textAlign: "center", color: TEXT.faint2, fontSize: 14, padding: "2px 0" }}>↓</div>}
        </div>
      ))}
    </div>
  );
}

function ArchitectureDiagram({ mainChain, parallelChains }: { mainChain: ArchitectureChain; parallelChains: ArchitectureChain[] }) {
  return (
    <div style={{ marginTop: 16, maxWidth: 420 }}>
      <Chain steps={mainChain.steps} />
      <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "16px 0", color: TEXT.faint, fontSize: 12 }}>
        <span style={{ flex: 1, height: 1, background: SURFACE.separatorInner }} />
        <span>+</span>
        <span style={{ flex: 1, height: 1, background: SURFACE.separatorInner }} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 20, maxWidth: 700 }}>
        {parallelChains.map((c, i) => (
          <div key={i}>
            {c.heading && <div style={{ fontSize: 11, color: TEXT.faint, marginBottom: 8, letterSpacing: "0.06em", textTransform: "uppercase" }}>{c.heading}</div>}
            <Chain steps={c.steps} />
          </div>
        ))}
      </div>
    </div>
  );
}

function RiskCard({ risk, last }: { risk: RankedRisk; last: boolean }) {
  return (
    <div style={{ display: "flex", gap: 16, padding: "16px 0", borderBottom: last ? "none" : `1px solid ${SURFACE.separatorInner}` }}>
      <div style={{ flex: "none", width: 34, fontFamily: FONT_MONO, fontSize: 19, fontWeight: 600, color: risk.rank === 1 ? ACCENT.amber : TEXT.faint2 }}>
        {String(risk.rank).padStart(2, "0")}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: TEXT.primary, marginBottom: 8 }}>{risk.title}</div>
        <BulletList items={risk.bullets} />
        <div style={{ marginTop: 10, display: "flex", gap: 8, fontSize: 13, lineHeight: 1.5, flexWrap: "wrap" }}>
          <span style={{ color: ACCENT.green, fontWeight: 600, flex: "none" }}>Mitigation:</span>
          <span style={{ color: TEXT.secondary2 }}>{risk.mitigation}</span>
        </div>
      </div>
    </div>
  );
}

function NumberedBehaviors({ items }: { items: string[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 14 }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
          <div
            style={{
              flex: "none",
              width: 24,
              height: 24,
              borderRadius: "50%",
              background: SURFACE.activeRow,
              color: TEXT.primary,
              fontSize: 12,
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {i + 1}
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: TEXT.primary, lineHeight: 1.5, paddingTop: 2 }}>{item}</div>
        </div>
      ))}
    </div>
  );
}

function ChipRow({ items }: { items: string[] }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      {items.map((b) => (
        <span key={b} style={{ fontSize: 12, color: TEXT.metadata, background: SURFACE.activeRow, borderRadius: 6, padding: "4px 10px" }}>
          {b}
        </span>
      ))}
    </div>
  );
}

function SectionShell({ id, num, title, children }: { id: string; num: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} data-section-anchor style={{ padding: "34px 0", borderBottom: `1px solid ${SURFACE.separatorInner}` }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 16 }}>
        <span style={{ fontFamily: FONT_MONO, fontSize: 13, color: TEXT.faint2 }}>{num}</span>
        <h2 style={{ fontSize: 20, fontWeight: 600, color: TEXT.primary, margin: 0 }}>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function ResponsibilitiesBlock({ s }: { s: ResponsibilitiesSection }) {
  return (
    <SectionShell id={s.id} num={s.num} title={s.title}>
      <p style={{ fontSize: 14, fontWeight: 500, color: TEXT.secondary2, margin: 0, maxWidth: 720, lineHeight: 1.55 }}>{s.framing}</p>
      <TwoColBlock left={s.llm} right={s.app} />
      {s.keyLines.map((k, i) => (
        <KeyLine key={i}>{k}</KeyLine>
      ))}
    </SectionShell>
  );
}

function RagCompareBlock({ s }: { s: RagCompareSection }) {
  return (
    <SectionShell id={s.id} num={s.num} title={s.title}>
      <BulletList items={s.bullets} />
      <KeyLine>{s.keyLine}</KeyLine>
      <div style={{ marginTop: 22 }}>
        <TwoColBlock left={s.compare.rag} right={s.compare.governed} />
      </div>
    </SectionShell>
  );
}

function RealVsSimplifiedBlock({ s }: { s: RealVsSimplifiedSection }) {
  return (
    <SectionShell id={s.id} num={s.num} title={s.title}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
        <div style={{ background: SURFACE.raised, borderRadius: 10, padding: 18 }}>
          <div style={{ fontSize: 11, letterSpacing: "0.08em", color: ACCENT.green, marginBottom: 12, textTransform: "uppercase", fontWeight: 700 }}>{s.real.heading}</div>
          <BulletList items={s.real.bullets} />
          <div style={{ marginTop: 14, fontSize: 12.5, color: TEXT.faint, fontStyle: "italic" }}>{s.real.note}</div>
        </div>
        <div style={{ background: "transparent", border: `1px dashed ${SURFACE.separator}`, borderRadius: 10, padding: 18 }}>
          <div style={{ fontSize: 11, letterSpacing: "0.08em", color: TEXT.faint2, marginBottom: 12, textTransform: "uppercase", fontWeight: 700 }}>{s.simplified.heading}</div>
          <BulletList items={s.simplified.bullets} tone="muted" />
        </div>
      </div>
      <KeyLine>{s.keyLine}</KeyLine>
    </SectionShell>
  );
}

function ArchitectureBlock({ s }: { s: ArchitectureSection }) {
  return (
    <SectionShell id={s.id} num={s.num} title={s.title}>
      <div style={{ fontSize: 12.5, color: TEXT.faint, fontStyle: "italic", marginBottom: 4 }}>{s.disclaimer}</div>
      <ArchitectureDiagram mainChain={s.mainChain} parallelChains={s.parallelChains} />
      <div style={{ marginTop: 22 }}>
        <BulletList items={s.bullets} />
      </div>
      <KeyLine>{s.keyLine}</KeyLine>
    </SectionShell>
  );
}

function BulletsSimpleBlock({ s }: { s: BulletsSimpleSection }) {
  return (
    <SectionShell id={s.id} num={s.num} title={s.title}>
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 10 }}>
        {s.bullets.map((item, i) => (
          <li key={i} style={{ display: "flex", gap: 10, fontSize: 13.5, lineHeight: 1.55, color: TEXT.strongSecondary2 }}>
            <span style={{ color: TEXT.faint2, flex: "none" }}>–</span>
            {typeof item === "string" ? (
              <span>{item}</span>
            ) : (
              <span>
                {item.text}
                <div style={{ marginTop: 6 }}>
                  <ChipRow items={item.sub} />
                </div>
              </span>
            )}
          </li>
        ))}
      </ul>
      <KeyLine>{s.keyLine}</KeyLine>
    </SectionShell>
  );
}

function RankedRisksBlock({ s }: { s: RankedRisksSection }) {
  return (
    <SectionShell id={s.id} num={s.num} title={s.title}>
      <div>
        {s.risks.map((r, i) => (
          <RiskCard key={r.rank} risk={r} last={i === s.risks.length - 1} />
        ))}
      </div>
      <KeyLine>{s.keyLine}</KeyLine>
    </SectionShell>
  );
}

function PhasesBlock({ s }: { s: PhasesSection }) {
  return (
    <SectionShell id={s.id} num={s.num} title={s.title}>
      <p style={{ fontSize: 14, fontWeight: 500, color: TEXT.secondary2, margin: "0 0 16px", maxWidth: 720, lineHeight: 1.55 }}>{s.opening}</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {s.phases.map((p) => (
          <div key={p.name} style={{ background: SURFACE.raised, borderRadius: 10, padding: 18 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: TEXT.primary }}>{p.name}</div>
              {p.badge && (
                <span style={{ fontSize: 11, fontWeight: 600, color: ACCENT.blue, background: "rgba(91,159,212,0.12)", borderRadius: 20, padding: "3px 10px" }}>{p.badge}</span>
              )}
            </div>
            <BulletList items={p.bullets} />
          </div>
        ))}
      </div>
      <KeyLine>{s.keyLine}</KeyLine>
    </SectionShell>
  );
}

function AdoptionBlock({ s }: { s: AdoptionSection }) {
  return (
    <SectionShell id={s.id} num={s.num} title={s.title}>
      <p style={{ fontSize: 14, fontWeight: 500, color: TEXT.secondary2, margin: 0, maxWidth: 720, lineHeight: 1.55 }}>{s.opening}</p>
      <NumberedBehaviors items={s.behaviors} />
      <div style={{ marginTop: 18 }}>
        <BulletList items={s.bullets} />
      </div>
      <div style={{ marginTop: 20, padding: 16, borderRadius: 10, border: `1px solid ${SURFACE.separatorInner2}` }}>
        <SectionEyebrow text="Adoption-stall signals" />
        <BulletList items={s.stallSignals} tone="muted" />
      </div>
      <KeyLine>{s.keyLine}</KeyLine>
    </SectionShell>
  );
}

function MeasurementBlock({ s }: { s: MeasurementSection }) {
  return (
    <SectionShell id={s.id} num={s.num} title={s.title}>
      <p style={{ fontSize: 14, fontWeight: 500, color: TEXT.secondary2, margin: 0, maxWidth: 720, lineHeight: 1.55 }}>{s.opening}</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16, marginTop: 14 }}>
        {s.groups.map((g) => (
          <div key={g.heading} style={{ background: SURFACE.raised, borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: TEXT.primary, marginBottom: 10 }}>{g.heading}</div>
            <BulletList items={g.bullets} />
          </div>
        ))}
      </div>
      <div style={{ marginTop: 20 }}>
        <SectionEyebrow text={s.diagnostic.heading} />
        <ChipRow items={s.diagnostic.bullets} />
      </div>
      <KeyLine>{s.keyLine}</KeyLine>
    </SectionShell>
  );
}

function renderSection(s: DiscussionSection) {
  switch (s.kind) {
    case "responsibilities":
      return <ResponsibilitiesBlock key={s.id} s={s} />;
    case "rag-compare":
      return <RagCompareBlock key={s.id} s={s} />;
    case "real-vs-simplified":
      return <RealVsSimplifiedBlock key={s.id} s={s} />;
    case "architecture":
      return <ArchitectureBlock key={s.id} s={s} />;
    case "bullets-simple":
      return <BulletsSimpleBlock key={s.id} s={s} />;
    case "ranked-risks":
      return <RankedRisksBlock key={s.id} s={s} />;
    case "phases":
      return <PhasesBlock key={s.id} s={s} />;
    case "adoption":
      return <AdoptionBlock key={s.id} s={s} />;
    case "measurement":
      return <MeasurementBlock key={s.id} s={s} />;
  }
}

function ProductThesisCard() {
  const t = PRODUCT_THESIS;
  return (
    <section style={{ padding: "36px 0 8px" }}>
      <div style={{ background: SURFACE.raised, borderRadius: 14, padding: "32px 36px", textAlign: "center" }}>
        <div style={{ fontSize: 21, fontWeight: 700, color: TEXT.primary, marginBottom: 22 }}>{t.heading}</div>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "center", gap: "8px 10px", marginBottom: 26 }}>
          {t.flow.map((step, i) => (
            <span key={step} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: TEXT.strongSecondary2, background: SURFACE.activeRow, borderRadius: 20, padding: "6px 14px", whiteSpace: "nowrap" }}>
                {step}
              </span>
              {i < t.flow.length - 1 && <span style={{ color: TEXT.faint2 }}>→</span>}
            </span>
          ))}
        </div>
        <div style={{ fontSize: 16, fontStyle: "italic", color: TEXT.strongSecondary2, lineHeight: 1.6, maxWidth: 640, margin: "0 auto 18px" }}>“{t.quote}”</div>
        <div style={{ fontSize: 15, fontWeight: 700, color: ACCENT.green }}>{t.final}</div>
      </div>
    </section>
  );
}

export function DiscussionGuide() {
  const contentRef = useRef<HTMLDivElement>(null);
  const [activeId, setActiveId] = useState<string>(DISCUSSION_SECTIONS[0].id);

  // Scrollspy: highlight whichever section is nearest the top of the
  // content column. Registered once - the section list is static authored
  // content, never changes at runtime.
  useEffect(() => {
    const root = contentRef.current;
    if (!root) return;
    const targets = Array.from(root.querySelectorAll<HTMLElement>("[data-section-anchor]"));
    if (targets.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        const top = visible[0];
        if (top?.target.id) setActiveId(top.target.id);
      },
      { root, rootMargin: "0px 0px -65% 0px", threshold: 0 },
    );
    targets.forEach((t) => observer.observe(t));
    return () => observer.disconnect();
  }, []);

  function jumpTo(id: string) {
    setActiveId(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div style={{ height: "100%", width: "100%", display: "flex", flexDirection: "column", background: SURFACE.app, overflow: "hidden" }}>
      <div style={{ flex: "none", padding: "26px 40px 20px", borderBottom: `1px solid ${SURFACE.separator}` }}>
        <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 10 }}>{DISCUSSION_GUIDE_HEADER.eyebrow}</div>
        <div style={{ fontSize: 26, fontWeight: 700, color: TEXT.primary, lineHeight: 1.2 }}>{DISCUSSION_GUIDE_HEADER.title}</div>
        <div style={{ fontSize: 15, color: TEXT.strongSecondary2, marginTop: 6 }}>{DISCUSSION_GUIDE_HEADER.tagline}</div>
        <div style={{ fontSize: 13.5, color: TEXT.secondary, marginTop: 10, maxWidth: 720, lineHeight: 1.55 }}>{DISCUSSION_GUIDE_HEADER.subtitle}</div>
      </div>

      <div className="flex flex-col lg:flex-row" style={{ flex: 1, minHeight: 0 }}>
        <nav
          className="w-full lg:w-56 lg:flex-none ap-scroll border-b lg:border-b-0 lg:border-r"
          style={{ borderColor: SURFACE.separator, padding: "18px 14px", overflowY: "auto" }}
        >
          <div className="flex flex-row flex-wrap gap-1 lg:flex-col lg:flex-nowrap lg:gap-0.5">
            {DISCUSSION_SECTIONS.map((s) => {
              const isActive = s.id === activeId;
              return (
                <button
                  key={s.id}
                  onClick={() => jumpTo(s.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    textAlign: "left",
                    padding: "8px 10px",
                    borderRadius: 7,
                    border: "none",
                    cursor: "pointer",
                    background: isActive ? SURFACE.activeRow : "transparent",
                    color: isActive ? TEXT.primary : TEXT.secondary2,
                    fontSize: 13,
                    fontWeight: isActive ? 600 : 500,
                    whiteSpace: "nowrap",
                  }}
                >
                  <span style={{ fontFamily: FONT_MONO, fontSize: 11, color: isActive ? ACCENT.blue : TEXT.faint }}>{s.num}</span>
                  {s.navLabel}
                </button>
              );
            })}
          </div>
        </nav>

        <div ref={contentRef} className="ap-scroll flex-1" style={{ minHeight: 0, overflowY: "auto", padding: "6px 40px 20px" }}>
          {DISCUSSION_SECTIONS.map(renderSection)}
          <ProductThesisCard />
        </div>
      </div>
    </div>
  );
}
