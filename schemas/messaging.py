from pydantic import BaseModel, Field
from typing import List, Dict, Any

class PlannerToCoderInstruction(BaseModel):
    """
    Message from the Planner to the Coder.
    """
    original_code: str
    goal: str

class CoderToEvaluatorSubmission(BaseModel):
    """
    Message from the Coder to the Evaluator.
    """
    original_code: str
    refactored_code: str
    test_file_path: str

class EvaluatorToCorrectorCritique(BaseModel):
    """
    Message from the Evaluator to the Corrector.
    """
    original_code: str
    refactored_code: str
    test_passed: bool
    performance_score: float
    critique: str

class CorrectorToCoderInstruction(BaseModel):
    """
    Message from the Corrector to the Coder.
    """
    original_code: str
    failed_code: str
    critique: str

class CausalFocus(BaseModel):
    """
    Structured causal analysis from the CausalAttentionWrapper.
    """
    change_type: str
    from_value: Any
    to_value: Any

class CausalCritique(BaseModel):
    """
    Structured critique from the EvaluatorAgent.
    """
    test_passed: bool
    causal_improvement: bool
    analysis: CausalFocus
    reason: str
