"use client";

import { useState } from "react";
import { ACCENT, FONT_MONO, SURFACE, TEXT, sentenceCase, titleCase } from "@/lib/design";
import type { PlanCreateResponse, PlanProposalResponse, ProposedPlannedAction } from "@/lib/types";

const ACTION_TYPE_LABEL: Record<string, string> = {
  renew: "Renew", renegotiate: "Renegotiate", test: "Test", expand: "Expand",
  pause: "Pause", review_measurement: "Review measurement", follow_up: "Follow up",
};

type Resolution = "approved" | "rejected";

function ActionCard({
  action, resolution, busy, onApprove, onReject,
}: {
  action: ProposedPlannedAction;
  resolution: Resolution | undefined;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  const resolved = Boolean(resolution);
  return (
    <div
      style={{
        border: `1px solid ${resolution === "approved" ? "rgba(79,185,141,0.3)" : resolution === "rejected" ? "rgba(201,112,122,0.3)" : SURFACE.nodeBorderResting}`,
        background: resolution === "approved" ? "rgba(79,185,141,0.05)" : resolution === "rejected" ? "rgba(201,112,122,0.05)" : SURFACE.nodeResting,
        borderRadius: 10, padding: 16, opacity: resolution === "rejected" ? 0.6 : 1,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 10, marginBottom: 8 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 11, letterSpacing: "0.06em", color: ACCENT.purple, fontFamily: FONT_MONO, marginBottom: 4 }}>
            {ACTION_TYPE_LABEL[action.action_type] ?? titleCase(action.action_type)} · {action.partner_name}
          </div>
          <div style={{ fontSize: 14.5, fontWeight: 600, color: TEXT.primary }}>{action.summary}</div>
        </div>
        {resolution && (
          <span style={{ fontSize: 11, fontFamily: FONT_MONO, color: resolution === "approved" ? ACCENT.green : "#c9707a", flex: "none" }}>
            {resolution === "approved" ? "✓ Approved" : "✕ Rejected"}
          </span>
        )}
      </div>
      <div style={{ fontSize: 13.5, lineHeight: 1.55, color: TEXT.secondary2, marginBottom: 10 }}>{action.rationale}</div>

      {action.duplicate_of_planned_action_id && (
        <div style={{ fontSize: 12.5, color: ACCENT.amber, marginBottom: 10 }}>
          ⚠ An open planned action already covers this partner + action type - review before approving a duplicate.
        </div>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: resolved ? 0 : 12 }}>
        {action.source_scenario_id && (
          <span style={{ fontSize: 10.5, letterSpacing: "0.05em", color: ACCENT.teal, fontFamily: FONT_MONO }}>SCENARIO: {action.source_scenario_id.toUpperCase()}</span>
        )}
        {action.supporting_memory_ids.length > 0 && (
          <span style={{ fontSize: 10.5, letterSpacing: "0.05em", color: ACCENT.blue, fontFamily: FONT_MONO }}>{action.supporting_memory_ids.length} MEMORY REF{action.supporting_memory_ids.length === 1 ? "" : "S"}</span>
        )}
        {action.supporting_campaign_ids.length > 0 && (
          <span style={{ fontSize: 10.5, letterSpacing: "0.05em", color: "#7ecec6", fontFamily: FONT_MONO }}>{action.supporting_campaign_ids.length} CAMPAIGN{action.supporting_campaign_ids.length === 1 ? "" : "S"}</span>
        )}
      </div>

      {!resolved && (
        <div style={{ display: "flex", gap: 8 }}>
          <button
            disabled={busy}
            onClick={onApprove}
            style={{ fontSize: 12.5, fontWeight: 600, padding: "7px 14px", borderRadius: 7, border: "none", background: ACCENT.green, color: "#0a1622", cursor: "pointer", opacity: busy ? 0.6 : 1 }}
          >
            Approve
          </button>
          <button
            disabled={busy}
            onClick={onReject}
            style={{ fontSize: 12.5, fontWeight: 600, padding: "7px 14px", borderRadius: 7, border: `1px solid ${SURFACE.separatorInner2}`, background: "transparent", color: TEXT.secondary2, cursor: "pointer", opacity: busy ? 0.6 : 1 }}
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}

export function PlanProposalPanel({
  proposal,
  createdPlan,
  busy,
  onCreatePlan,
}: {
  proposal: PlanProposalResponse;
  createdPlan: PlanCreateResponse | null;
  busy: boolean;
  onCreatePlan: (approved: ProposedPlannedAction[]) => void;
}) {
  const [resolved, setResolved] = useState<Record<string, Resolution>>({});

  const approvedActions = proposal.proposed_actions.filter((a) => resolved[a.temp_id] === "approved");
  const allResolved = proposal.proposed_actions.length > 0 && proposal.proposed_actions.every((a) => resolved[a.temp_id]);

  if (createdPlan) {
    return (
      <>
        <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 4 }}>ACCOUNT PLANNING</div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <span style={{ fontSize: 16, fontWeight: 600, color: TEXT.primary }}>{createdPlan.plan.name}</span>
          <span style={{ fontSize: 10.5, letterSpacing: "0.06em", color: ACCENT.green, fontFamily: FONT_MONO }}>APPROVED PLAN</span>
        </div>
        <div style={{ fontSize: 13.5, color: TEXT.secondary2, marginBottom: 12 }}>
          {createdPlan.plan.actions.length} action{createdPlan.plan.actions.length === 1 ? "" : "s"} persisted.
          {createdPlan.skipped_duplicate_actions.length > 0 && (
            <> {createdPlan.skipped_duplicate_actions.length} skipped as duplicate of an already-open action.</>
          )}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {createdPlan.plan.actions.map((a) => (
            <div key={a.id} style={{ fontSize: 13.5, color: TEXT.secondary2, border: `1px solid ${SURFACE.nodeBorderResting}`, borderRadius: 8, padding: "10px 12px" }}>
              <span style={{ color: TEXT.primary, fontWeight: 600 }}>{ACTION_TYPE_LABEL[a.action_type] ?? titleCase(a.action_type)}</span> — {a.partner_name}: {a.summary}
            </div>
          ))}
        </div>
      </>
    );
  }

  return (
    <>
      <div style={{ fontSize: 11, letterSpacing: "0.09em", color: TEXT.faint, marginBottom: 4 }}>ACCOUNT PLANNING</div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <span style={{ fontSize: 16, fontWeight: 600, color: TEXT.primary }}>{proposal.plan_name}</span>
        <span style={{ fontSize: 10.5, letterSpacing: "0.06em", color: ACCENT.amber, fontFamily: FONT_MONO }}>PROPOSED PLAN</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
        <span style={{ fontSize: 10, letterSpacing: "0.06em", color: ACCENT.purple, fontFamily: FONT_MONO }}>MODEL SYNTHESIS</span>
        <span style={{ fontSize: 13.5, color: TEXT.secondary2 }}>{proposal.objective}</span>
      </div>

      <div style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 6 }}>
          <div style={{ fontSize: 12.5, color: TEXT.metadata }}>Current planning context</div>
          <span style={{ fontSize: 10, letterSpacing: "0.06em", color: ACCENT.teal, fontFamily: FONT_MONO }}>STRUCTURED SOURCE DATA</span>
        </div>
        <div style={{ fontSize: 13, color: TEXT.secondary2 }}>
          {proposal.context.partners.length} partner{proposal.context.partners.length === 1 ? "" : "s"} considered
          {proposal.context.client.current_strategy.length > 0 && (
            <> · current strategy: {proposal.context.client.current_strategy.map((c) => sentenceCase(c.value)).join(", ")}</>
          )}
          {proposal.context.existing_open_actions.length > 0 && <> · {proposal.context.existing_open_actions.length} already-open action(s) on file</>}
        </div>
      </div>

      {proposal.proposed_actions.length === 0 ? (
        <div style={{ fontSize: 13.5, color: TEXT.faint, fontStyle: "italic" }}>No partner in scope has enough evidence to ground a proposed action right now.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
          {proposal.proposed_actions.map((a) => (
            <ActionCard
              key={a.temp_id}
              action={a}
              resolution={resolved[a.temp_id]}
              busy={busy}
              onApprove={() => setResolved((r) => ({ ...r, [a.temp_id]: "approved" }))}
              onReject={() => setResolved((r) => ({ ...r, [a.temp_id]: "rejected" }))}
            />
          ))}
        </div>
      )}

      {proposal.proposed_actions.length > 0 && (
        <div style={{ display: "flex", gap: 10, alignItems: "center", borderTop: `1px solid ${SURFACE.separatorInner2}`, paddingTop: 14 }}>
          {!allResolved && (
            <button
              disabled={busy}
              onClick={() => setResolved(Object.fromEntries(proposal.proposed_actions.map((a) => [a.temp_id, "approved"])))}
              style={{ fontSize: 12.5, fontWeight: 600, padding: "8px 14px", borderRadius: 8, border: `1px solid ${SURFACE.separatorInner2}`, background: "transparent", color: TEXT.secondary2, cursor: "pointer" }}
            >
              Approve all
            </button>
          )}
          <button
            disabled={busy || approvedActions.length === 0}
            onClick={() => onCreatePlan(approvedActions)}
            style={{
              fontSize: 13, fontWeight: 600, padding: "9px 16px", borderRadius: 8, border: "none",
              background: ACCENT.blue, color: "#0a1622", cursor: "pointer",
              opacity: busy || approvedActions.length === 0 ? 0.5 : 1,
            }}
          >
            Create plan{approvedActions.length > 0 ? ` (${approvedActions.length} approved)` : ""}
          </button>
        </div>
      )}
    </>
  );
}
