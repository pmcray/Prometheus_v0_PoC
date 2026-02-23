#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC-AGI v0.96: LLM-Guided Symbolic Search

Uses Google Gemini to provide semantic understanding of ARC-AGI tasks
and suggest parametric transformation sequences.

Key Features:
- Updated for v0.96 parametric operations (19 operations)
- Suggests both operation names and potential parameter values
- Integration with PrometheusARC_v096_MetaGood
"""

import os
import json
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from arc_parametric_operations import PARAMETRIC_OPERATIONS

@dataclass
class TaskAnalysisv096:
    """LLM's analysis of an ARC task for v0.96"""
    task_type: str
    key_transformations: List[str]
    suggested_program: List[Tuple[str, Dict]]  # [(op_name, params), ...]
    confidence: float
    reasoning: str

class GeminiTaskAnalyzerV096:
    """
    Uses Google Gemini to analyze ARC tasks and suggest parametric sequences.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if GEMINI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None

        # 19 Parametric Operations from v0.96c
        self.ops = PARAMETRIC_OPERATIONS
        
        # Statistics
        self.analyses_count = 0

    def analyze_task(self, task_id: str, train_examples: List[Dict]) -> TaskAnalysisv096:
        """Analyze task and suggest parametric program."""
        if not self.model:
            return self._fallback_analysis("Gemini not available")

        self.analyses_count += 1
        prompt = self._build_prompt(task_id, train_examples)

        try:
            response = self.model.generate_content(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            print(f"  [LLM] API Error: {e}")
            return self._fallback_analysis(str(e))

    def _build_prompt(self, task_id: str, train_examples: List[Dict]) -> str:
        ops_desc = "\n".join([f"- {name}: {spec['description']}" for name, spec in self.ops.items()])
        
        examples_text = ""
        for i, ex in enumerate(train_examples[:3], 1):
            examples_text += f"\nExample {i}:\nIn:\n{np.array(ex['input'])}\nOut:\n{np.array(ex['output'])}\n"

        return f"""Analyze this ARC-AGI task (ID: {task_id}).
IDENTIFY THE TRANSFORMATION RULE.

AVAILABLE OPERATIONS:
{ops_desc}

TRAINING EXAMPLES:
{examples_text}

OUTPUT FORMAT (JSON):
{{
  "task_type": "type",
  "key_transformations": ["desc"],
  "suggested_program": [
    ["op_name", {{"param": "value"}}]
  ],
  "confidence": 0.9,
  "reasoning": "why"
}}

Rules: 
- Use ONLY operations from the list.
- Keep programs short (1-3 ops).
- If no params needed, use {{}}.
"""

    def _parse_response(self, text: str) -> TaskAnalysisv096:
        try:
            # Simple JSON extraction
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            data = json.loads(text.strip())
            
            # Validate operations
            raw_program = data.get('suggested_program', [])
            valid_program = []
            for item in raw_program:
                if isinstance(item, list) and len(item) == 2:
                    op, params = item
                    if op in self.ops:
                        valid_program.append((op, params))
            
            return TaskAnalysisv096(
                task_type=data.get('task_type', 'unknown'),
                key_transformations=data.get('key_transformations', []),
                suggested_program=valid_program,
                confidence=float(data.get('confidence', 0.0)),
                reasoning=data.get('reasoning', '')
            )
        except Exception as e:
            return self._fallback_analysis(f"Parse error: {e}")

    def _fallback_analysis(self, msg: str) -> TaskAnalysisv096:
        return TaskAnalysisv096("unknown", [msg], [], 0.0, msg)
