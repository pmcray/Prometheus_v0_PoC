
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

class CausalNodeType(str, Enum):
    CONCEPT = "concept"
    TOOL = "tool"
    EXPERT = "expert"
    PROBLEM = "problem"

class CausalNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the node (e.g., 'Memory Management')")
    type: CausalNodeType
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExpertSignature(BaseModel):
    expert_id: str
    capabilities: List[str] = Field(..., description="Causal variables this expert can manipulate")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    load_factor: float = Field(0.0, ge=0.0, le=1.0)

class MutationMethod(str, Enum):
    REFACTOR = "REFACTOR"
    OPTIMIZE = "OPTIMIZE"
    CROSSOVER = "CROSSOVER"
    CAUSAL = "CAUSAL"

class MutationRecord(BaseModel):
    genotype_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    parent_ids: List[uuid.UUID] = Field(default_factory=list)
    mutation_method: MutationMethod
    fitness_score: float = 0.0
    phenotype_desc: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)

class SafetyCheckResult(BaseModel):
    is_safe: bool
    violation_type: Optional[str] = None
    description: str = ""
    principle_violated: Optional[str] = None
    severity: int = Field(0, ge=0, le=10)

class ContextFrame(BaseModel):
    goal: str
    active_variables: List[str] = Field(default_factory=list)
    causal_constraints: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
