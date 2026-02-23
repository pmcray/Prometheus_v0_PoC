#!/usr/bin/env python3
"""
Prometheus v0.82 - LLM Task Analyzer

Uses Google Gemini to provide semantic understanding of ARC-AGI tasks
and suggest primitive transformation sequences.

Key Innovation: Combine LLM semantic reasoning with symbolic verification
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
    print("⚠️  google-generativeai not installed. Install with: pip install google-generativeai")


@dataclass
class TaskAnalysis:
    """LLM's analysis of an ARC task"""
    task_type: str  # "rotation", "color_mapping", "spatial", "object_detection", etc.
    key_transformations: List[str]  # High-level transformations identified
    suggested_primitives: List[str]  # Specific primitive names to try
    confidence: float  # 0-1, how confident the LLM is
    reasoning: str  # LLM's explanation


class GeminiTaskAnalyzer:
    """
    Uses Google Gemini to analyze ARC tasks and suggest primitive sequences.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        """
        Args:
            api_key: Google AI API key (if None, reads from GOOGLE_API_KEY env var)
            model_name: Gemini model to use (flash is fast/cheap, pro is better)
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package not installed")

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set. Set it with: export GOOGLE_API_KEY='your-key'")

        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

        # Available primitives (from ARCPrimitives)
        self.available_primitives = [
            'identity', 'rotate_90', 'rotate_180', 'rotate_270',
            'flip_h', 'flip_v', 'transpose', 'diagonal_flip',
            'scale_2x', 'scale_3x', 'tile_2x2', 'tile_3x3',
            'tile_2x1', 'tile_1x3',
            'gravity_down', 'gravity_up',
            'fill_zeros', 'remove_bg',
            'swap_01', 'color_inc', 'invert',
            'isolate_1', 'isolate_2',
            'border', 'center', 'pad_1',
            'compress_h', 'compress_v',
            'mirror_h', 'mirror_v',
            'hollow', 'count_colors', 'swap_max_min',
            'extend_edges', 'crop',
            'sym_h', 'sym_v',
            'color_pos', 'downsample', 'checkerboard',
            'overlay_max'
        ]

        # Prompt template
        self.system_prompt = self._build_system_prompt()

        # Statistics
        self.analyses_count = 0
        self.api_calls_count = 0
        self.total_cost_estimate = 0.0

    def _build_system_prompt(self) -> str:
        """Build the system prompt that explains the task to Gemini"""
        primitives_list = "\n".join(f"- {p}" for p in self.available_primitives)

        return f"""You are an expert at analyzing ARC-AGI (Abstraction and Reasoning Corpus) tasks.

ARC-AGI tasks involve transforming a 2D grid (input) into another 2D grid (output) following a pattern.
Each task has 2-3 training examples showing input→output pairs, and you must identify the transformation rule.

AVAILABLE PRIMITIVES:
{primitives_list}

PRIMITIVE DESCRIPTIONS:
- rotate_90/180/270: Rotate grid clockwise
- flip_h/flip_v: Flip horizontally/vertically
- transpose/diagonal_flip: Matrix transpose operations
- scale_2x/3x: Scale up by repeating cells
- tile_2x2/3x3: Tile the grid in NxN pattern
- gravity_down/up: Non-zero cells fall down/up
- fill_zeros: Fill zeros with most common color
- invert: Invert colors (9-color)
- border/center: Extract border or center region
- crop: Crop to non-zero content
- mirror_h/mirror_v: Mirror and concatenate
- hollow: Convert filled regions to outlines
- swap_colors: Swap specific colors
- and more...

YOUR TASK:
1. Analyze the input→output examples
2. Identify the transformation pattern
3. Suggest a sequence of 1-3 primitives that could produce the transformation
4. Explain your reasoning

IMPORTANT:
- Only suggest primitives from the AVAILABLE PRIMITIVES list above
- Suggest 1-3 primitives in sequence (e.g., ["rotate_90", "flip_h"])
- Be specific and confident
- If unsure, suggest the most likely options

OUTPUT FORMAT (JSON):
{{
  "task_type": "rotation|color_mapping|spatial|tiling|...",
  "key_transformations": ["description of what happens"],
  "suggested_primitives": ["prim1", "prim2"],
  "confidence": 0.8,
  "reasoning": "explanation"
}}
"""

    def analyze_task(self,
                     task_id: str,
                     train_examples: List[Dict],
                     max_retries: int = 3) -> TaskAnalysis:
        """
        Analyze an ARC task using Gemini.

        Args:
            task_id: Task identifier
            train_examples: List of training examples [{'input': grid, 'output': grid}, ...]
            max_retries: Number of retries if API fails

        Returns:
            TaskAnalysis with LLM's suggestions
        """
        self.analyses_count += 1

        # Build prompt with examples
        prompt = self._build_task_prompt(task_id, train_examples)

        # Call Gemini with retries
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                self.api_calls_count += 1

                # Estimate cost (~$0.01 per call for flash, ~$0.05 for pro)
                cost_per_call = 0.01 if "flash" in self.model.model_name else 0.05
                self.total_cost_estimate += cost_per_call

                # Parse response
                analysis = self._parse_response(response.text)
                return analysis

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠️  Gemini API error (attempt {attempt+1}/{max_retries}): {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"  ❌ Gemini API failed after {max_retries} attempts: {e}")
                    # Return fallback analysis
                    return self._fallback_analysis()

    def _build_task_prompt(self, task_id: str, train_examples: List[Dict]) -> str:
        """Build the specific prompt for this task"""
        examples_text = ""

        for i, example in enumerate(train_examples[:3], 1):  # Max 3 examples
            input_grid = np.array(example['input'])
            output_grid = np.array(example['output'])

            examples_text += f"\nExample {i}:\n"
            examples_text += f"Input shape: {input_grid.shape}\n"
            examples_text += f"Input:\n{input_grid}\n"
            examples_text += f"Output shape: {output_grid.shape}\n"
            examples_text += f"Output:\n{output_grid}\n"

        prompt = f"""{self.system_prompt}

TASK ID: {task_id}

TRAINING EXAMPLES:
{examples_text}

Now analyze this task and suggest which primitives to use.
Respond ONLY with valid JSON in the format specified above.
"""
        return prompt

    def _parse_response(self, response_text: str) -> TaskAnalysis:
        """Parse LLM's JSON response into TaskAnalysis"""
        try:
            # Extract JSON from response (may have markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text.strip()

            data = json.loads(json_text)

            # Validate primitives are in our list
            suggested = data.get('suggested_primitives', [])
            valid_primitives = [p for p in suggested if p in self.available_primitives]

            if not valid_primitives:
                print(f"  ⚠️  LLM suggested invalid primitives: {suggested}")
                valid_primitives = ['identity']  # Fallback

            return TaskAnalysis(
                task_type=data.get('task_type', 'unknown'),
                key_transformations=data.get('key_transformations', []),
                suggested_primitives=valid_primitives,
                confidence=float(data.get('confidence', 0.5)),
                reasoning=data.get('reasoning', '')
            )

        except Exception as e:
            print(f"  ⚠️  Failed to parse LLM response: {e}")
            print(f"  Response: {response_text[:200]}...")
            return self._fallback_analysis()

    def _fallback_analysis(self) -> TaskAnalysis:
        """Return a safe fallback when LLM fails"""
        return TaskAnalysis(
            task_type='unknown',
            key_transformations=['Could not analyze'],
            suggested_primitives=['identity'],
            confidence=0.0,
            reasoning='LLM analysis failed, using fallback'
        )

    def get_statistics(self) -> Dict:
        """Get usage statistics"""
        return {
            'analyses_count': self.analyses_count,
            'api_calls_count': self.api_calls_count,
            'estimated_cost_usd': self.total_cost_estimate,
            'avg_cost_per_analysis': self.total_cost_estimate / self.analyses_count if self.analyses_count > 0 else 0
        }


def test_analyzer():
    """Test the analyzer on a simple task"""
    print("="*80)
    print("🧪 Testing Gemini Task Analyzer")
    print("="*80)

    # Check if API key is set
    if not os.environ.get("GOOGLE_API_KEY"):
        print("\n❌ GOOGLE_API_KEY not set!")
        print("   Set it with: export GOOGLE_API_KEY='your-api-key'")
        print("   Get a key from: https://makersuite.google.com/app/apikey")
        return

    # Create analyzer
    try:
        analyzer = GeminiTaskAnalyzer()
        print(f"✅ Analyzer initialized with model: {analyzer.model.model_name}")
        print(f"✅ {len(analyzer.available_primitives)} primitives available")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize analyzer: {e}")
        return

    # Create a simple test task (rotation)
    test_task = {
        'train': [
            {
                'input': [[1, 2], [3, 4]],
                'output': [[3, 1], [4, 2]]
            },
            {
                'input': [[5, 6], [7, 8]],
                'output': [[7, 5], [8, 6]]
            }
        ]
    }

    print("Test Task (90° rotation):")
    print(f"  Input:  [[1, 2], [3, 4]]")
    print(f"  Output: [[3, 1], [4, 2]]")
    print()

    print("Analyzing with Gemini...")
    analysis = analyzer.analyze_task("test_rotation", test_task['train'])

    print()
    print("="*80)
    print("📊 ANALYSIS RESULTS")
    print("="*80)
    print(f"Task Type: {analysis.task_type}")
    print(f"Key Transformations: {analysis.key_transformations}")
    print(f"Suggested Primitives: {analysis.suggested_primitives}")
    print(f"Confidence: {analysis.confidence:.2f}")
    print(f"Reasoning: {analysis.reasoning}")
    print()

    # Statistics
    stats = analyzer.get_statistics()
    print("="*80)
    print("💰 USAGE STATISTICS")
    print("="*80)
    print(f"API Calls: {stats['api_calls_count']}")
    print(f"Estimated Cost: ${stats['estimated_cost_usd']:.4f}")
    print()

    print("✅ Test complete!")


if __name__ == "__main__":
    test_analyzer()
