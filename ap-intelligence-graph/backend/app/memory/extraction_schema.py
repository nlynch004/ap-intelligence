"""Pydantic validation for raw extraction-agent output.

The LLM (or the mock provider) returns plain dicts. Before anything from
that output is allowed to become a `MemoryCandidate` row, it must pass
through `ExtractedClaimIn` here. This is a distinct, stricter model from
`schemas.CandidateClaimPayload` (the API-facing shape) because it validates
the raw, undefaulted output straight off the model call - the boundary
where a malformed or out-of-range value must be caught, not the shape
already-defaulted candidates take once inside the app.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ClaimClassIn = Literal[
    "verified_fact",
    "account_preference",
    "historical_observation",
    "decision",
    "outcome",
    "hypothesis",
    "portfolio_pattern",
]


class ExtractedClaimIn(BaseModel):
    type: str = "client_preference"
    subject_type: Literal["client", "creator", "publisher", "campaign"]
    subject_id: str = ""
    subject_label: str = ""
    predicate: str
    value: str
    claim_class: ClaimClassIn
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""

    @field_validator("predicate", "value")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @model_validator(mode="after")
    def _subject_id_required_unless_client(self) -> "ExtractedClaimIn":
        # subject_type == "client" always gets its subject_id overwritten
        # with the caller's client_id downstream (manager.py), so the model
        # doesn't need to supply one. Every other subject_type must name a
        # concrete subject - a blank one can't be conflict-matched or
        # persisted meaningfully.
        if self.subject_type != "client" and not self.subject_id.strip():
            raise ValueError("subject_id is required for non-client subjects")
        return self
