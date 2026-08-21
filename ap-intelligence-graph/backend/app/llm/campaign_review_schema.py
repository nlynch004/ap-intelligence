from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class RawCampaignReviewOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str
    what_worked: list[str] = []
    what_is_uncertain: list[str] = []
    planning_implications: list[str] = []
    candidate_lessons: list[dict[str, Any]] = []

    @field_validator("summary")
    @classmethod
    def _summary_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("summary must not be blank")
        return v


def validate_raw_campaign_review(raw: object) -> dict:
    return RawCampaignReviewOut(**raw).model_dump()
