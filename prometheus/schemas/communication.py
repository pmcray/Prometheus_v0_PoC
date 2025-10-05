"""
JSON Schema definitions for inter-agent communication protocol
Implements the robust communication system from v0.19
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum

class MessageType(str, Enum):
    PLANNER_TO_CODER = "planner_to_coder"
    CODER_TO_EVALUATOR = "coder_to_evaluator"
    EVALUATOR_TO_CORRECTOR = "evaluator_to_corrector"
    CORRECTOR_TO_CODER = "corrector_to_coder"
    MCS_INTERVENTION = "mcs_intervention"
    MEMORY_QUERY = "memory_query"
    MEMORY_RESPONSE = "memory_response"

class AgentMessage(BaseModel):
    """Base message schema for all inter-agent communication"""
    message_type: MessageType
    sender: str
    recipient: str
    timestamp: str
    run_id: str
    payload: Dict[str, Any]

class PlannerToCoderInstruction(BaseModel):
    """Schema for Planner -> Coder instructions"""
    task_description: str
    initial_code: str
    performance_requirements: Dict[str, Any]
    causal_focus: Optional[Dict[str, Any]] = None
    meta_prompt: Optional[str] = None

class CoderToEvaluatorSubmission(BaseModel):
    """Schema for Coder -> Evaluator submissions"""
    original_code: str
    refactored_code: str
    reasoning: str
    confidence_score: float = Field(ge=0.0, le=1.0)

class CausalAnalysis(BaseModel):
    """Schema for causal analysis results"""
    change_type: str
    complexity_before: Dict[str, Any]
    complexity_after: Dict[str, Any]
    causal_diff: Dict[str, Any]
    improvement_detected: bool

class DynamicAnalysis(BaseModel):
    """Schema for dynamic performance analysis"""
    status: str
    execution_time_ms: Dict[str, float]
    peak_memory_mb: Dict[str, float]
    profile_data: Optional[Dict[str, Any]] = None

class EvaluatorToCorrectorCritique(BaseModel):
    """Schema for Evaluator -> Corrector critiques"""
    test_passed: bool
    functional_correctness: bool
    causal_analysis: CausalAnalysis
    dynamic_analysis: Optional[DynamicAnalysis] = None
    evaluation_confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_level: str
    historical_context: List[Dict[str, str]]
    reason: str
    improvement_achieved: bool

class SelfReferentialCritique(EvaluatorToCorrectorCritique):
    """Enhanced critique with self-referential elements (v0.25)"""
    meta_analysis: Optional[Dict[str, Any]] = None
    attention_targets: List[str] = []
    cognitive_load: float = 0.0

class CorrectorToCoderInstruction(BaseModel):
    """Schema for Corrector -> Coder instructions"""
    critique: EvaluatorToCorrectorCritique
    correction_strategy: str
    specific_guidance: str
    analogical_hints: List[str] = []
    meta_instructions: Optional[str] = None

class MemoryQuery(BaseModel):
    """Schema for memory system queries"""
    query_type: str  # "failure", "success", "pattern"
    code_snippet: str
    problem_description: str
    similarity_threshold: float = 0.7
    max_results: int = 5

class MemoryResponse(BaseModel):
    """Schema for memory system responses"""
    results: List[Dict[str, Any]]
    similarity_scores: List[float]
    metadata: Dict[str, Any]

class MCSSafetyViolation(BaseModel):
    """Schema for MCS safety violations"""
    violation_type: str
    severity: str
    description: str
    evidence: Dict[str, Any]
    recommended_action: str

class ConstitutionalViolation(MCSSafetyViolation):
    """Enhanced safety violation for constitutional governance"""
    principle_violated: str
    causal_path_analysis: str
    meta_reasoning: str