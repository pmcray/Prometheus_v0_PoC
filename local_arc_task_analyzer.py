#!/usr/bin/env python3
"""
Local Foundation Model ARC Task Analyzer (v0.82-local)

Uses Phi-3 or DeepSeek locally for semantic task understanding.
No cloud API dependency - runs entirely on Jetson Orin via llama.cpp.
"""

import subprocess
import tempfile
import json
import re
import os
from typing import List, Dict, Optional
from pathlib import Path
import numpy as np


class LocalARCAnalyzer:
    """Analyze ARC tasks using local foundation model"""

    def __init__(self,
                 model_path: str = "/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf",
                 model_type: str = "phi3"):
        """
        Args:
            model_path: Path to GGUF model file
            model_type: "phi3" or "deepseek"
        """
        self.model_path = model_path
        self.model_type = model_type

        # All 38 available primitives from ARCPrimitives
        self.available_primitives = [
            'identity', 'rotate_90', 'rotate_180', 'rotate_270',
            'flip_h', 'flip_v', 'transpose', 'diag_flip',
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

        # Statistics
        self.analyses_count = 0
        self.successes = 0
        self.failures = 0

    def analyze_task(self, task_id: str, examples: List[Dict]) -> List[str]:
        """
        Analyze task and suggest primitives

        Args:
            task_id: Task identifier
            examples: List of {'input': grid, 'output': grid}

        Returns:
            List of suggested primitive names (1-3 operations)
        """
        self.analyses_count += 1

        prompt = self._build_prompt(examples)

        try:
            response = self._generate(prompt, max_tokens=512)
            primitives = self._parse_primitives(response)

            if primitives and primitives != ['identity']:
                self.successes += 1
            else:
                self.failures += 1

            return primitives

        except Exception as e:
            print(f"  ⚠️  Analysis error: {e}")
            self.failures += 1
            return ['identity']  # Safe fallback

    def _build_prompt(self, examples: List[Dict]) -> str:
        """Build analysis prompt optimized for Phi-3"""

        # Format examples (limit to 1 for context, keep prompt under 4k tokens)
        ex_text = ""
        for i, ex in enumerate(examples[:1], 1):
            input_grid = np.array(ex['input'])
            output_grid = np.array(ex['output'])

            # Summarize grid instead of full dump if large
            in_h, in_w = input_grid.shape
            out_h, out_w = output_grid.shape

            ex_text += f"Example {i}:\n"
            ex_text += f"Input: {in_h}x{in_w} grid, colors {np.unique(input_grid).tolist()}\n"
            ex_text += f"Output: {out_h}x{out_w} grid, colors {np.unique(output_grid).tolist()}\n"

            # Show small grids fully, large grids as summary
            if in_h <= 5 and in_w <= 5:
                ex_text += f"Input:\n{input_grid}\n"
            if out_h <= 5 and out_w <= 5:
                ex_text += f"Output:\n{output_grid}\n"
            ex_text += "\n"

        # Build Phi-3 optimized prompt (VERY SHORT to fit 4k context)
        prompt = f"""ARC-AGI grid transformation task.

{ex_text}

Common operations:
rotate_90/180/270, flip_h/v, transpose, scale_2x/3x, tile_2x2/3x3,
gravity_down/up, crop, invert, mirror_h/v, sym_h/v, border, center

Task: Suggest 1-3 operations that transform input→output.

Response (JSON only):
{{"operations": ["op1"], "confidence": 0.8}}

Response:"""

        return prompt

    def _generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate using llama-cli"""

        # Write prompt to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            # Run llama-cli with optimized settings for Jetson
            cmd = [
                '/home/pmc/llama.cpp/build/bin/llama-cli',
                '-m', self.model_path,
                '-f', prompt_file,
                '-n', str(max_tokens),
                '--temp', '0.3',           # Lower temp for focused output
                '-ngl', '35',              # GPU layers (Jetson Orin)
                '-c', '2048',              # Context size (reduced for shorter prompts)
                '--no-display-prompt',     # Clean output
                '-b', '512',               # Batch size
                '--mlock'                  # Lock model in RAM
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute max
            )

            if result.returncode != 0:
                raise RuntimeError(f"llama-cli failed: {result.stderr}")

            return result.stdout.strip()

        finally:
            # Cleanup temp file
            try:
                Path(prompt_file).unlink()
            except OSError:
                pass

    def _parse_primitives(self, response: str) -> List[str]:
        """Extract primitive suggestions from response"""

        # Try JSON parse first
        try:
            # Find JSON object in response
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                ops = data.get('operations', [])

                # Validate and filter primitives
                valid_ops = [op for op in ops if op in self.available_primitives]

                if valid_ops:
                    return valid_ops[:3]  # Max 3 operations
        except Exception as e:
            pass

        # Fallback: Search for mentioned primitives in response
        found = []
        response_lower = response.lower()

        for prim in self.available_primitives:
            if prim in response_lower:
                found.append(prim)
                if len(found) >= 3:
                    break

        # Return found primitives or safe fallback
        return found if found else ['identity']

    def get_statistics(self) -> Dict:
        """Get analyzer statistics"""
        return {
            'analyses_count': self.analyses_count,
            'successes': self.successes,
            'failures': self.failures,
            'success_rate': self.successes / self.analyses_count if self.analyses_count > 0 else 0
        }


def test_analyzer():
    """Quick test of the analyzer"""
    print("="*70)
    print("🧪 Testing Local ARC Task Analyzer")
    print("="*70)

    # Check model exists
    model_path = "/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf"
    if not Path(model_path).exists():
        print(f"❌ Model not found: {model_path}")
        return

    print(f"✅ Found model: {model_path}")
    print()

    # Create analyzer
    analyzer = LocalARCAnalyzer(model_path)
    print(f"✅ Analyzer initialized")
    print(f"📊 {len(analyzer.available_primitives)} primitives available")
    print()

    # Test task 1: Simple rotation
    print("Test 1: Rotation Task")
    print("-" * 70)
    test_task1 = [
        {
            'input': [[1, 2], [3, 4]],
            'output': [[3, 1], [4, 2]]
        },
        {
            'input': [[5, 6], [7, 8]],
            'output': [[7, 5], [8, 6]]
        }
    ]

    print("Input 1: [[1, 2], [3, 4]]")
    print("Output 1: [[3, 1], [4, 2]]")
    print()
    print("Analyzing with Phi-3...")

    result1 = analyzer.analyze_task("test_rotation", test_task1)
    print(f"✅ Suggested operations: {result1}")
    print(f"   Expected: ['rotate_90'] or similar")
    print()

    # Test task 2: Scaling
    print("Test 2: Scaling Task")
    print("-" * 70)
    test_task2 = [
        {
            'input': [[1, 2], [3, 4]],
            'output': [[1, 1, 2, 2], [1, 1, 2, 2], [3, 3, 4, 4], [3, 3, 4, 4]]
        }
    ]

    print("Input: [[1, 2], [3, 4]]")
    print("Output: [[1, 1, 2, 2], ...")
    print()
    print("Analyzing with Phi-3...")

    result2 = analyzer.analyze_task("test_scale", test_task2)
    print(f"✅ Suggested operations: {result2}")
    print(f"   Expected: ['scale_2x'] or similar")
    print()

    # Statistics
    stats = analyzer.get_statistics()
    print("="*70)
    print("📊 Statistics")
    print("="*70)
    print(f"Analyses: {stats['analyses_count']}")
    print(f"Successes: {stats['successes']}")
    print(f"Failures: {stats['failures']}")
    print(f"Success rate: {stats['success_rate']:.1%}")
    print()

    print("✅ Test complete!")


if __name__ == "__main__":
    test_analyzer()
