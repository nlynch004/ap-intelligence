from pydantic import BaseModel, ConfigDict


class RawHistoricalSummaryOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str = ""
    material_changes: list[str] = []
    current_state: str = ""
    historical_context: list[str] = []


def validate_raw_historical_summary(raw: object) -> dict:
    return RawHistoricalSummaryOut(**raw).model_dump()
