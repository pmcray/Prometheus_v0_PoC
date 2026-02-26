"""
Cognitive Trace Logger — Prometheus v0.98 (WP-06)

Captures a detailed, structured log of the agent's internal reasoning process,
providing the raw data for self-referential critique.
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field

@dataclass
class CognitiveStep:
    """A single step in the reasoning process."""
    timestamp: float
    step_type: str  # e.g., "thought", "tool_call", "observation", "hypothesis"
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

class CognitiveTrace:
    """A complete trace of a reasoning session."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.start_time = time.time()
        self.steps: List[CognitiveStep] = []
        self.final_result: Any = None

    def add_step(self, step_type: str, content: Any, **metadata):
        step = CognitiveStep(
            timestamp=time.time(),
            step_type=step_type,
            content=content,
            metadata=metadata
        )
        self.steps.append(step)

    def set_result(self, result: Any):
        self.final_result = result

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "steps": [asdict(s) for s in self.steps],
            "final_result": self.final_result
        }

class CognitiveTraceLogger:
    """
    Manages the recording and storage of cognitive traces.
    """
    def __init__(self, log_dir: str = "logs/cognitive_traces"):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.active_traces: Dict[str, CognitiveTrace] = {}

    def start_session(self, session_id: str) -> CognitiveTrace:
        trace = CognitiveTrace(session_id)
        self.active_traces[session_id] = trace
        return trace

    def end_session(self, session_id: str):
        if session_id in self.active_traces:
            trace = self.active_traces[session_id]
            self.save_trace(trace)
            del self.active_traces[session_id]

    def save_trace(self, trace: CognitiveTrace):
        file_path = os.path.join(self.log_dir, f"{trace.session_id}.json")
        with open(file_path, "w") as f:
            json.dump(trace.to_dict(), f, indent=2)

import os
