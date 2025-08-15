
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class CausalCritique(BaseModel):
    test_passed: bool
    causal_improvement: bool
    reason: str

class SelfReferentialCritique(CausalCritique):
    evaluation_confidence: float = Field(..., description="The evaluator's confidence in its own analysis, from 0.0 to 1.0.")
    uncertainty_level: str = Field(..., description="The evaluator's uncertainty level (e.g., 'low', 'medium', 'high').")
    historical_context: List[Dict[str, Any]] = Field(..., description="A list of similar past failures.")
