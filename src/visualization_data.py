from pydantic import BaseModel, Field
from typing import List

class AssemblyState(BaseModel):
    component_id: str = Field(..., description="The unique identifier for the component (e.g., 'CoderAgent').")
    component_type: str = Field(..., description="The type of the component (e.g., 'Assembly', 'Subassembly').")
    activation_level: float = Field(..., ge=0.0, le=1.0, description="The current activation level of the component (0.0 to 1.0).")
    connections: List[str] = Field(..., description="A list of component IDs this component is currently connected to.")
