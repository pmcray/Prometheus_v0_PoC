from pydantic import BaseModel
from typing import List, Optional

class CausalAnalysis(BaseModel):
    change_type: str  # e.g., "IMPROVEMENT", "REGRESSION", "NO_CHANGE"
    from_complexity: int
    to_complexity: int

class HistoricalContext(BaseModel):
    run_id: str
    critique_summary: str

class PerformanceMetric(BaseModel):
    original: float
    new: float
    delta: float

class DynamicAnalysis(BaseModel):
    status: str  # "COMPLETED" or "FAILED"
    execution_time_ms: Optional[PerformanceMetric] = None
    peak_memory_mb: Optional[PerformanceMetric] = None

class SelfReferentialCritique(BaseModel):
    test_passed: bool
    causal_analysis: CausalAnalysis
    dynamic_analysis: Optional[DynamicAnalysis] = None
    evaluation_confidence: float
    uncertainty_level: str  # "low", "medium", "high"
    historical_context: Optional[List[HistoricalContext]] = None
    reason: str
