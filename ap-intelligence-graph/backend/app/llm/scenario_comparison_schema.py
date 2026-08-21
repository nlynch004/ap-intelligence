from pydantic import BaseModel, ConfigDict, Field, field_validator


class RawScenarioComparisonOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    preferred_scenario_id: str
    comparison_summary: str
    tradeoffs: list[str] = []
    uncertainties: list[str] = []
    questions_before_finalizing: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("preferred_scenario_id", "comparison_summary")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


def validate_raw_scenario_comparison(raw: object) -> dict:
    return RawScenarioComparisonOut(**raw).model_dump()
