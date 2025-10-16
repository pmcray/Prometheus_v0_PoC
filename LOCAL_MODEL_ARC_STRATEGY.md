# Local Foundation Model Strategy for ARC-AGI v0.82+

**Date**: 2025-10-15
**Constraint**: No cloud API access (Google Gemini not available)
**Available**: Local foundation models via llama.cpp
**Goal**: Improve ARC-AGI from 1.25% baseline

---

## Executive Summary

**Challenge**: v0.82 was designed for Google Gemini API (not available)

**Solution**: Adapt semantic guidance approach using local foundation models

**Available Models**:
- Phi-3-mini-4k-instruct (2.3GB, 3.8B params) - Better for reasoning
- DeepSeek-Coder-1.3B (834MB, 1.3B params) - Better for code

**Strategy**: Use local model for task analysis, symbolic verification for correctness

---

## Available Resources

### Models

```bash
/home/pmc/ioi_models/
├── Phi-3-mini-4k-instruct-q4.gguf (2.3GB)
└── deepseek-coder-1.3b-instruct.Q4_K_M.gguf (834MB)
```

### Infrastructure

```bash
/home/pmc/llama.cpp/build/bin/llama-cli  # ✅ Available
```

### Current Performance

| Approach | Accuracy | Status |
|----------|----------|--------|
| Baseline Evolution (v0.69) | 1.25% (5/400) | ✅ Works |
| Meta-Learning (v0.78) | 1.25% (5/400) | ✅ Works |
| Transfer Learning (v0.79) | 1.25% (5/400) | ❌ Failed |
| **Target (local model)** | **3-8%** | **Goal** |

---

## Strategy: Local Model Semantic Guidance

### Core Idea

**Original v0.82 (Gemini)**:
```
Gemini analyzes task → suggests primitives → symbolic verification
```

**Adapted v0.82 (Local)**:
```
Local model analyzes task → suggests primitives → symbolic verification
```

**Key Insight**: Even a small local model can provide useful semantic hints!

---

## Approach Options

### Option A: Phi-3 Task Analyzer ⭐ RECOMMENDED

**Use Phi-3 (3.8B) for semantic understanding**

**Why Phi-3**:
- Larger model (3.8B vs 1.3B)
- Strong reasoning capabilities
- Proven to work on IOI Bronze (63% accuracy)
- Better at understanding task semantics

**Implementation**:

```python
class LocalARCTaskAnalyzer:
    """Use Phi-3 to analyze ARC tasks"""

    def __init__(self):
        self.model = LocalModelInference(
            "/home/pmc/ioi_models/Phi-3-mini-4k-instruct-q4.gguf"
        )
        self.primitives = ['rotate_90', 'flip_h', 'scale_2x', ...]  # 38 primitives

    def analyze_task(self, train_examples):
        prompt = self._build_prompt(train_examples)
        response = self.model.generate(prompt, max_tokens=512)  # Short output
        return self._parse_suggestions(response)

    def _build_prompt(self, examples):
        return f"""Analyze this grid transformation task.

Input grid 1: {examples[0]['input']}
Output grid 1: {examples[0]['output']}

Input grid 2: {examples[1]['input']}
Output grid 2: {examples[1]['output']}

Available operations: {', '.join(self.primitives)}

What operations would transform input to output?
Suggest 1-3 operations from the list above.

Response format:
Operations: [operation1, operation2]
Reasoning: brief explanation

Response:"""
```

**Expected Performance**: 3-6% (12-24 tasks)

**Advantages**:
- No API dependency
- Fast inference (Jetson Orin GPU)
- Proven model performance

**Limitations**:
- Won't match Gemini's understanding
- May hallucinate operations
- Limited by 4k context

---

### Option B: DeepSeek-Coder Primitive Suggestion

**Use DeepSeek-Coder for pattern analysis**

**Why DeepSeek**:
- Specialized for code/patterns
- Smaller/faster (1.3B)
- Can run multiple attempts quickly

**Implementation**:

```python
def suggest_primitives_deepseek(examples):
    prompt = f"""# Grid transformation pattern

input1 = {examples[0]['input']}
output1 = {examples[0]['output']}

# What operations transform input to output?
# Available: rotate_90, flip_h, scale_2x, tile_2x2, etc.

operations = ['"""

    response = deepseek.generate(prompt, max_tokens=64)
    return parse_operation_list(response)
```

**Expected Performance**: 2-4% (8-16 tasks)

**Advantages**:
- Very fast inference
- Code-focused = pattern-focused
- Can do multiple samples per task

**Limitations**:
- Smaller model = less reasoning
- Less semantic understanding

---

### Option C: Hybrid Ensemble

**Combine both models**

```python
def analyze_task_ensemble(examples):
    # Get suggestions from both models
    phi3_suggestions = phi3_analyzer.analyze(examples)
    deepseek_suggestions = deepseek_analyzer.analyze(examples)

    # Combine suggestions
    all_primitives = phi3_suggestions + deepseek_suggestions

    # Try all unique combinations
    for pattern in generate_combinations(all_primitives):
        fitness = evaluate_symbolically(pattern, examples)
        if fitness >= 1.0:
            return pattern  # Perfect match!

    # Fallback to evolution
    return evolve(examples)
```

**Expected Performance**: 4-8% (16-32 tasks)

**Advantages**:
- Best of both models
- More diverse suggestions
- Higher success rate

**Limitations**:
- Slower (2x inference)
- More complex

---

## Implementation Plan

### Phase 1: Setup llama-cli Path

```bash
# Add to PATH
export PATH="/home/pmc/llama.cpp/build/bin:$PATH"

# Or create symlink
sudo ln -s /home/pmc/llama.cpp/build/bin/llama-cli /usr/local/bin/llama-cli

# Test
llama-cli --version
```

### Phase 2: Create Local Task Analyzer

**File**: `local_arc_task_analyzer.py`

```python
#!/usr/bin/env python3
"""
Local Foundation Model ARC Task Analyzer (v0.82-local)

Uses Phi-3 or DeepSeek locally for semantic task understanding.
"""

import subprocess
import tempfile
import json
import re
from typing import List, Dict
from pathlib import Path

class LocalARCAnalyzer:
    """Analyze ARC tasks using local foundation model"""

    def __init__(self, model_path: str, model_type: str = "phi3"):
        """
        Args:
            model_path: Path to GGUF model
            model_type: "phi3" or "deepseek"
        """
        self.model_path = model_path
        self.model_type = model_type
        self.available_primitives = [
            'identity', 'rotate_90', 'rotate_180', 'rotate_270',
            'flip_h', 'flip_v', 'transpose', 'diagonal_flip',
            'scale_2x', 'scale_3x', 'tile_2x2', 'tile_3x3',
            'gravity_down', 'gravity_up', 'invert', 'crop',
            # ... all 38 primitives
        ]

    def analyze_task(self, examples: List[Dict]) -> List[str]:
        """
        Analyze task and suggest primitives

        Returns:
            List of suggested primitive names
        """
        prompt = self._build_prompt(examples)
        response = self._generate(prompt, max_tokens=512)
        primitives = self._parse_primitives(response)
        return primitives

    def _build_prompt(self, examples: List[Dict]) -> str:
        """Build analysis prompt"""
        if self.model_type == "phi3":
            return self._build_phi3_prompt(examples)
        else:
            return self._build_deepseek_prompt(examples)

    def _build_phi3_prompt(self, examples: List[Dict]) -> str:
        """Phi-3 prompt optimized for reasoning"""
        ex_text = ""
        for i, ex in enumerate(examples[:2], 1):
            ex_text += f"Example {i}:\n"
            ex_text += f"Input: {ex['input']}\n"
            ex_text += f"Output: {ex['output']}\n\n"

        return f"""You are analyzing a grid transformation puzzle.

{ex_text}

Available operations: {', '.join(self.available_primitives[:20])}
(and more: scale, tile, gravity, color operations, etc.)

Task: Identify which 1-3 operations transform input to output.

Think step-by-step:
1. What changed? (size, orientation, colors, pattern)
2. Which operations could cause this?
3. Suggest 1-3 operations in order

Response format (JSON):
{{"operations": ["op1", "op2"], "reasoning": "brief explanation"}}

Response:"""

    def _build_deepseek_prompt(self, examples: List[Dict]) -> str:
        """DeepSeek prompt optimized for pattern recognition"""
        return f"""# Grid transformation pattern

input1 = {examples[0]['input']}
output1 = {examples[0]['output']}

input2 = {examples[1]['input']}
output2 = {examples[1]['output']}

# Pattern analysis
# What operations: rotate_90, flip_h, scale_2x, tile_2x2, invert, crop?

suggested_operations = ['"""

    def _generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate using llama-cli"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            cmd = [
                'llama-cli',
                '-m', self.model_path,
                '-f', prompt_file,
                '-n', str(max_tokens),
                '--temp', '0.3',
                '-ngl', '35',  # GPU layers
                '--no-display-prompt'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.stdout.strip()
        finally:
            Path(prompt_file).unlink()

    def _parse_primitives(self, response: str) -> List[str]:
        """Extract primitive suggestions from response"""
        # Try JSON parse first
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                ops = data.get('operations', [])
                # Validate against available primitives
                return [op for op in ops if op in self.available_primitives]
        except:
            pass

        # Fallback: find any mentioned primitives
        found = []
        for prim in self.available_primitives:
            if prim in response:
                found.append(prim)
                if len(found) >= 3:
                    break

        return found if found else ['identity']  # Safe fallback
```

### Phase 3: Integrate with Symbolic Verifier

**File**: `prometheus_arc_local_guided.py`

```python
#!/usr/bin/env python3
"""
Prometheus ARC Local-Guided Solver (v0.82-local)

Uses local foundation model (Phi-3/DeepSeek) for semantic guidance
with symbolic verification.
"""

from local_arc_task_analyzer import LocalARCAnalyzer
from prometheus_arc_regularized import ARCPrimitives, PrometheusARCRegularized
import numpy as np

class PrometheusARCLocalGuided:
    """Local-model-guided ARC solver"""

    def __init__(self, model_path: str, model_type: str = "phi3"):
        self.analyzer = LocalARCAnalyzer(model_path, model_type)
        self.primitives = ARCPrimitives()
        self.baseline = PrometheusARCRegularized()

        # Build primitive methods
        self.primitive_methods = {
            'rotate_90': ARCPrimitives.rotate_90,
            'flip_h': ARCPrimitives.flip_horizontal,
            # ... all primitives
        }

    def solve_task(self, train_examples, task_id):
        """Solve task using local model guidance"""

        # 1. Get model suggestions
        print(f"  [Local Model] Analyzing task {task_id}...")
        suggested_prims = self.analyzer.analyze_task(train_examples)
        print(f"  [Local Model] Suggested: {suggested_prims}")

        # 2. Try suggested patterns
        best_fitness = 0.0
        best_pattern = suggested_prims

        # Try exact suggestion
        fitness = self._evaluate_pattern(suggested_prims, train_examples)
        if fitness >= 1.0:
            return {'pattern': suggested_prims, 'fitness': 1.0, 'method': 'local_direct'}
        best_fitness = fitness

        # 3. Try variations
        variations = self._generate_variations(suggested_prims)
        for var in variations:
            fitness = self._evaluate_pattern(var, train_examples)
            if fitness > best_fitness:
                best_fitness = fitness
                best_pattern = var
            if fitness >= 1.0:
                return {'pattern': var, 'fitness': 1.0, 'method': 'local_variation'}

        # 4. Fallback to evolution if needed
        if best_fitness < 0.5:  # Model suggestions not helpful
            print(f"  [Fallback] Using evolution...")
            return self._evolve(train_examples)

        return {'pattern': best_pattern, 'fitness': best_fitness, 'method': 'local_partial'}

    def _evaluate_pattern(self, pattern, examples):
        """Symbolically evaluate pattern"""
        if not pattern:
            return 0.0

        correct = 0
        for ex in examples:
            input_grid = np.array(ex['input'])
            expected = np.array(ex['output'])

            try:
                predicted = self._apply_pattern(pattern, input_grid)
                if np.array_equal(predicted, expected):
                    correct += 1
            except:
                pass

        return correct / len(examples)

    def _apply_pattern(self, pattern, grid):
        """Apply pattern to grid"""
        output = grid.copy()
        for prim_name in pattern:
            if prim_name in self.primitive_methods:
                method = self.primitive_methods[prim_name]
                output = method(output)
        return output

    def _generate_variations(self, pattern):
        """Generate pattern variations"""
        variations = []
        common = ['rotate_90', 'flip_h', 'flip_v', 'transpose', 'invert']

        # Add common primitives
        for prim in common:
            if prim not in pattern:
                variations.append(pattern + [prim])
                variations.append([prim] + pattern)

        # Single primitives from original
        for prim in pattern:
            variations.append([prim])

        return variations[:15]

    def _evolve(self, examples):
        """Fallback evolution"""
        train_tuples = [(np.array(ex['input']), np.array(ex['output']))
                       for ex in examples]
        result = self.baseline.evolve_for_task(train_tuples, max_generations=100)
        return {
            'pattern': [op.name for op in result.operations],
            'fitness': result.fitness,
            'method': 'evolution_fallback'
        }
```

---

## Expected Performance

### Conservative Estimate (3%)

**Assumptions**:
- Local model provides useful hints for 30-40% of tasks
- Of those hints, 25% lead to solutions
- Math: 400 tasks × 35% hinted × 25% solved = 12 tasks

**Result**: 12/400 (3%) - **2.4x improvement**

### Realistic Estimate (5%)

**Assumptions**:
- Phi-3 provides useful hints for 50% of tasks
- Of those hints, 20% directly solve, 10% via variations
- Math: 400 × 50% × 30% = 20 tasks

**Result**: 20/400 (5%) - **4x improvement**

### Optimistic Estimate (8%)

**Assumptions**:
- Ensemble (Phi-3 + DeepSeek) covers 60% of tasks
- Success rate 30% with variations
- Better fallback evolution
- Math: 400 × 60% × 35% = 32 tasks

**Result**: 32/400 (8%) - **6.4x improvement**

---

## Advantages vs Cloud API Approach

### What We Lose

❌ Gemini's superior reasoning (175B+ params vs 3.8B)
❌ Long context window (32k vs 4k)
❌ Continuous updates and improvements

### What We Gain

✅ **No API dependency** - works offline
✅ **No cost** - unlimited inference
✅ **Fast inference** - GPU acceleration on Jetson
✅ **Privacy** - data stays local
✅ **Customizable** - can fine-tune models
✅ **Reproducible** - same model, same results

---

## Implementation Timeline

### Day 1: Setup and Test (2-3 hours)

1. Fix llama-cli PATH
2. Create `local_arc_task_analyzer.py`
3. Test on 3 simple tasks manually
4. Verify prompt engineering works

### Day 2: Integration (3-4 hours)

1. Create `prometheus_arc_local_guided.py`
2. Build primitive mapping
3. Implement variation generation
4. Test on 10 tasks

### Day 3: Full Evaluation (2-3 hours + overnight)

1. Run on all 400 evaluation tasks
2. Compare to baseline
3. Analyze failure modes
4. Document results

### Day 4: Optimization (if needed)

1. Tune prompts based on failures
2. Try DeepSeek ensemble
3. Adjust variation strategy
4. Re-evaluate

---

## Risk Mitigation

### Risk 1: Local Model Too Weak

**Mitigation**:
- Try both Phi-3 and DeepSeek
- Use ensemble approach
- Keep evolution fallback
- Lower expectations (3% still good!)

### Risk 2: Slow Inference

**Mitigation**:
- GPU acceleration via llama.cpp
- Short prompts (512 tokens max)
- Cache responses per cluster
- Parallel processing possible

### Risk 3: Poor Prompt Engineering

**Mitigation**:
- Start with simple prompts
- Iterate based on manual testing
- Copy successful patterns from IOI
- Add few-shot examples

---

## Success Criteria

### Minimum Viable (2-3%)

- 8-12 tasks solved (2-2.4x improvement)
- Local model provides useful hints
- Infrastructure works reliably

### Target (4-6%)

- 16-24 tasks solved (3.2-4.8x improvement)
- Phi-3 reasoning effective
- Variation generation successful

### Stretch (7-10%)

- 28-40 tasks solved (5.6-8x improvement)
- Ensemble approach working
- Approaching competitive performance

---

## Recommendation

**Proceed with Option A (Phi-3 Task Analyzer)**

**Why**:
1. Phi-3 proven on IOI Bronze (63%)
2. Better reasoning than DeepSeek
3. Simple to implement
4. Realistic 4-6% target
5. No external dependencies

**Timeline**: 3-4 days to full evaluation

**Expected Result**: 4-6% (16-24 tasks) with potential for 7-10% with optimization

---

## Next Steps

1. **Setup llama-cli PATH** (5 minutes)
2. **Create local analyzer** (1-2 hours)
3. **Test on 3 tasks manually** (30 minutes)
4. **Integrate with solver** (2 hours)
5. **Test on 10 tasks** (1 hour)
6. **Full 400-task evaluation** (overnight)

---

*Strategy Date: 2025-10-15*
*Status: Ready to Implement*
*Expected Performance: 4-6% (realistic), 7-10% (optimistic)*
*Timeline: 3-4 days*
