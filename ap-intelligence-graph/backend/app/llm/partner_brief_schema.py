from pydantic import BaseModel, ConfigDict, field_validator


class RawPartnerBriefOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    relationship_summary: str
    performance_summary: str
    what_to_know: list[str] = []
    negotiation_considerations: list[str] = []
    measurement_considerations: list[str] = []
    open_questions: list[str] = []
    planning_implications: list[str] = []

    @field_validator("relationship_summary", "performance_summary")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


def validate_raw_partner_brief(raw: object) -> dict:
    return RawPartnerBriefOut(**raw).model_dump()
