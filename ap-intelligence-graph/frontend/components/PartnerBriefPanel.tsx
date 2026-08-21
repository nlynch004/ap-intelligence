"use client";

import { ACCENT, FONT_MONO, TEXT, predicateLabel, sentenceCase } from "@/lib/design";
import type { PartnerBriefEvidence } from "@/lib/types";

function fmtMoney(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function fmtRoas(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `${v.toFixed(2)}x`;
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 8 }}>{label}</div>
      {children}
    </div>
  );
}

function EvidenceRow({ nodeId, onHighlight, children }: { nodeId: string; onHighlight?: (ids: string[]) => void; children: React.ReactNode }) {
  return (
    <div
      onClick={onHighlight ? () => onHighlight([nodeId]) : undefined}
      style={{ cursor: onHighlight ? "pointer" : "default" }}
      title={onHighlight ? "Highlight in graph" : undefined}
    >
      {children}
    </div>
  );
}

function SourceTag({ children, color }: { children: React.ReactNode; color: string }) {
  return <span style={{ fontSize: 10.5, letterSpacing: "0.06em", color, fontFamily: FONT_MONO }}>{children}</span>;
}

export function PartnerBriefPanel({
  evidence,
  onHighlight,
}: {
  evidence: PartnerBriefEvidence;
  onHighlight?: (ids: string[]) => void;
}) {
  const { partner, team_experience, campaigns, performance_stats, relationship_history, measurement_cautions, client_context, prior_decisions, outcomes } = evidence;

  return (
    <>
      <Block label="RELATIONSHIP">
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: 16, fontWeight: 600, color: TEXT.primary }}>{partner.name}</span>
          <SourceTag color={ACCENT.teal}>STRUCTURED SOURCE DATA</SourceTag>
        </div>
        <div style={{ fontSize: 13, color: TEXT.metadata }}>
          {partner.kind}
          {partner.platform ? ` · ${partner.platform}` : ""}
          {partner.follower_tier ? ` · ${partner.follower_tier} tier` : ""}
          {partner.record_relationship_status ? ` · ${partner.record_relationship_status.replace(/_/g, " ")}` : ""}
        </div>
        {partner.partner_note && (
          <div style={{ fontSize: 13, color: TEXT.secondary2, marginTop: 6, fontStyle: "italic" }}>
            &ldquo;{partner.partner_note}&rdquo; <span style={{ fontStyle: "normal", color: TEXT.faint }}>(record note, not governed memory)</span>
          </div>
        )}
        {partner.synthetic && <div style={{ fontSize: 11, letterSpacing: "0.08em", color: "#6b6288", marginTop: 8 }}>SYNTHETIC</div>}

        {team_experience.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {team_experience.map((t) => (
              <EvidenceRow key={t.team_member_id} nodeId={`team_member:${t.team_member_id}`} onHighlight={onHighlight}>
                <div style={{ fontSize: 13.5, color: TEXT.strongSecondary2 }}>
                  {t.name} <span style={{ color: TEXT.faint }}>({t.role})</span> — worked with this partner
                </div>
              </EvidenceRow>
            ))}
          </div>
        )}
      </Block>

      <Block label="PERFORMANCE">
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 13.5, color: TEXT.strongSecondary2 }}>
            {performance_stats.campaign_count} campaign{performance_stats.campaign_count === 1 ? "" : "s"} on file
          </span>
          <SourceTag color={ACCENT.teal}>STRUCTURED SOURCE DATA</SourceTag>
        </div>
        {performance_stats.campaign_count > 0 && (
          <div style={{ fontSize: 13, color: TEXT.metadata, marginBottom: 10 }}>
            Most recent: {fmtRoas(performance_stats.most_recent_roas)} ROAS · avg {fmtRoas(performance_stats.average_roas)}
            {performance_stats.average_engagement_rate != null && <> · avg engagement {(performance_stats.average_engagement_rate * 100).toFixed(1)}%</>}
            {performance_stats.fee_change_pct != null && <> · fee {performance_stats.fee_change_pct >= 0 ? "+" : ""}{performance_stats.fee_change_pct.toFixed(1)}% since first campaign</>}
            {performance_stats.revenue_trend && <> · revenue {performance_stats.revenue_trend}</>}
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {campaigns.map((c) => (
            <EvidenceRow key={c.campaign_id} nodeId={`campaign:${c.campaign_id}`} onHighlight={onHighlight}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10, fontSize: 13.5, color: TEXT.strongSecondary2 }}>
                <span>{c.month_label}</span>
                <span style={{ color: TEXT.secondary }}>{fmtMoney(c.fee)} → {fmtMoney(c.attributed_revenue)}</span>
                <span style={{ fontFamily: FONT_MONO, fontSize: 12.5, color: ACCENT.green }}>{fmtRoas(c.attributed_roas)}</span>
              </div>
            </EvidenceRow>
          ))}
        </div>
      </Block>

      <Block label="RELEVANT GOVERNED MEMORY">
        <div style={{ marginBottom: 6 }}>
          <SourceTag color={ACCENT.blue}>GOVERNED MEMORY</SourceTag>
        </div>
        {relationship_history.length === 0 && client_context.length === 0 ? (
          <div style={{ fontSize: 13.5, color: TEXT.faint, fontStyle: "italic" }}>No governed memory on file yet for this partner or the current strategy context.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 14, lineHeight: 1.5 }}>
            {relationship_history.map((m) => (
              <EvidenceRow key={m.claim_id} nodeId={`memory_claim:${m.claim_id}`} onHighlight={onHighlight}>
                <span style={{ color: TEXT.metadata }}>{predicateLabel(m.predicate)}</span>
                <br />
                <span style={{ color: TEXT.primary }}>{sentenceCase(m.value)}</span>
                <span style={{ fontSize: 11, color: TEXT.faint }}> · confidence {m.confidence.toFixed(2)}</span>
              </EvidenceRow>
            ))}
            {client_context.map((m) => (
              <EvidenceRow key={m.claim_id} nodeId={`memory_claim:${m.claim_id}`} onHighlight={onHighlight}>
                <span style={{ color: TEXT.metadata }}>{predicateLabel(m.predicate)} (current Northwind strategy)</span>
                <br />
                <span style={{ color: TEXT.primary }}>{sentenceCase(m.value)}</span>
              </EvidenceRow>
            ))}
          </div>
        )}
      </Block>

      <Block label="MEASUREMENT CONSIDERATIONS">
        {measurement_cautions.length === 0 ? (
          <div style={{ fontSize: 13.5, color: TEXT.secondary2 }}>No open measurement caution is on file for this partner&rsquo;s campaigns.</div>
        ) : (
          <div style={{ background: "rgba(201,151,90,0.06)", borderRadius: 10, padding: 14 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              <span style={{ color: ACCENT.amber, fontSize: 12 }}>△</span>
              <span style={{ fontSize: 13, color: ACCENT.amber, fontWeight: 600 }}>Unverified hypothesis</span>
            </div>
            {measurement_cautions.map((c, i) => (
              <EvidenceRow key={c.claim_id} nodeId={`memory_claim:${c.claim_id}`} onHighlight={onHighlight}>
                <div style={{ marginBottom: i === measurement_cautions.length - 1 ? 0 : 14 }}>
                  <div style={{ fontSize: 14, color: "#d5cbb8", fontWeight: 600, marginBottom: 6 }}>{sentenceCase(c.value)}</div>
                  <div style={{ fontSize: 14, color: "#a89b85", lineHeight: 1.55 }}>{c.summary}</div>
                  <div style={{ fontSize: 12, fontFamily: FONT_MONO, color: "#8a7e6b", marginTop: 8 }}>
                    {c.status.replace(/_/g, " ")} · confidence {c.confidence.toFixed(2)}
                  </div>
                </div>
              </EvidenceRow>
            ))}
          </div>
        )}
      </Block>

      {(prior_decisions.length > 0 || outcomes.length > 0) && (
        <Block label="PRIOR DECISIONS & OUTCOMES">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {prior_decisions.map((d) => (
              <EvidenceRow key={d.decision_id} nodeId={`decision:${d.decision_id}`} onHighlight={onHighlight}>
                <div style={{ fontSize: 13.5, color: TEXT.strongSecondary2 }}>
                  <span style={{ color: ACCENT.green }}>✓</span> {sentenceCase(d.summary)}
                  <span style={{ color: TEXT.faint }}> ({d.status})</span>
                </div>
                {typeof d.terms?.base_fee === "number" && (
                  <div style={{ fontSize: 12.5, color: TEXT.metadata, marginTop: 2 }}>
                    {fmtMoney(d.terms.base_fee as number)} base
                    {typeof d.terms.performance_bonus_pct === "number" && ` + ${d.terms.performance_bonus_pct}% bonus`}
                  </div>
                )}
              </EvidenceRow>
            ))}
            {outcomes.map((o) => (
              <EvidenceRow key={o.outcome_id} nodeId={`outcome:${o.outcome_id}`} onHighlight={onHighlight}>
                <div style={{ fontSize: 13.5, color: TEXT.strongSecondary2 }}>
                  Outcome: {sentenceCase(o.outcome_label)}
                  {o.is_simulated && <span style={{ color: ACCENT.amber }}> · SIMULATED</span>}
                </div>
              </EvidenceRow>
            ))}
          </div>
        </Block>
      )}
    </>
  );
}
