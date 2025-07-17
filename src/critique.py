
from pydantic import BaseModel

class CausalCritique(BaseModel):
    test_passed: bool
    causal_improvement: bool
    reason: str
