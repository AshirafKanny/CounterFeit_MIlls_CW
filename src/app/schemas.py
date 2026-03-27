from pydantic import BaseModel


class PredictionResponse(BaseModel):
    label: str
    note_state: str
    recommendation: str
    amount: str
    amount_confidence: float
    confidence: float
    details: dict[str, float]
