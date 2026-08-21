from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendedTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_fee: float = Field(gt=0)
    performance_bonus_pct: float = Field(ge=0, le=100)
    bonus_basis: str

    @field_validator("bonus_basis")
    @classmethod
    def _bonus_basis_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("bonus_basis must not be blank")
        return v


class RawRecommendationOut(BaseModel):

    model_config = ConfigDict(extra="ignore")

    recommendation: str
    recommended_terms: RecommendedTerms
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainties: list[str] = []
    explanation: str = ""

    @field_validator("recommendation")
    @classmethod
    def _recommendation_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("recommendation must not be blank")
        return v


def validate_raw_recommendation(raw: object) -> dict:
    return RawRecommendationOut(**raw).model_dump()
