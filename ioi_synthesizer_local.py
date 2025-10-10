#!/usr/bin/env python3
"""
IOI Code Synthesizer with Local Model Support (v0.75)

Supports both cloud (Gemini) and local (llama.cpp) models for code generation.
Local models recommended for Jetson Orin Nano: DeepSeek-Coder-1.3B, Phi-2/3, CodeLlama-7B-4bit
"""

import os
import re
import json
from typing import List, Dict, Optional
from pathlib import Path
import subprocess
import tempfile

# Try importing cloud LLM
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Import primitives for code cache
from ioi_primitives import IOIPrimitives


class LocalModelInference:
    """Interface to llama.cpp for local model inference"""

    def __init__(self, model_path: str, n_gpu_layers: int = 35, n_ctx: int = 4096):
        """
        Args:
            model_path: Path to GGUF model file
            n_gpu_layers: Number of layers to offload to GPU
            n_ctx: Context window size
        """
        self.model_path = model_path
        self.n_gpu_layers = n_gpu_layers
        self.n_ctx = n_ctx
        self.available = self._check_availability()

    def _check_availability(self) -> bool:
        """Check if llama.cpp main binary is available"""
        try:
            result = subprocess.run(
                ['which', 'llama-cli'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False

    def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 2048) -> str:
        """
        Generate text using llama.cpp

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens

        Returns:
            Generated text
        """
        if not self.available:
            raise RuntimeError("llama-cli not found. Install llama.cpp first.")

        # Write prompt to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            # Run llama.cpp
            cmd = [
                'llama-cli',
                '-m', self.model_path,
                '-f', prompt_file,
                '--temp', str(temperature),
                '-n', str(max_tokens),
                '-ngl', str(self.n_gpu_layers),
                '-c', str(self.n_ctx),
                '--no-display-prompt'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                raise RuntimeError(f"llama-cli failed: {result.stderr}")

            return result.stdout.strip()

        finally:
            os.unlink(prompt_file)


class IOICodeSynthesizer:
    """Generate code from algorithm primitives using local or cloud LLM"""

    def __init__(self,
                 api_key: str = None,
                 local_model_path: str = None,
                 use_local: bool = False):
        """
        Args:
            api_key: Google API key for Gemini (cloud)
            local_model_path: Path to local GGUF model
            use_local: Prefer local model over cloud
        """
        self.primitives = IOIPrimitives()
        self.primitive_code_cache = self._build_primitive_code_cache()

        # Setup model backends
        self.use_local = use_local
        self.local_model = None
        self.cloud_model = None

        if use_local and local_model_path:
            print(f"🔧 Initializing local model: {local_model_path}")
            self.local_model = LocalModelInference(local_model_path)
            if not self.local_model.available:
                print("⚠️  llama-cli not found, falling back to cloud/mock")
                self.use_local = False

        if not use_local and GEMINI_AVAILABLE and api_key:
            print("☁️  Using Gemini cloud model")
            genai.configure(api_key=api_key)
            self.cloud_model = genai.GenerativeModel('gemini-1.5-flash')

        # Determine active mode
        if self.use_local and self.local_model and self.local_model.available:
            self.mode = "local"
            print(f"✅ Local model mode active")
        elif self.cloud_model:
            self.mode = "cloud"
            print(f"✅ Cloud model mode active")
        else:
            self.mode = "mock"
            print(f"⚠️  Mock mode (no LLM available)")

    def _build_primitive_code_cache(self) -> Dict[str, str]:
        """Cache primitive implementations for synthesis"""
        import inspect

        cache = {}
        for name, method in inspect.getmembers(IOIPrimitives, predicate=inspect.isfunction):
            if not name.startswith('_'):
                source = inspect.getsource(method)
                cache[name] = source

        return cache

    def synthesize(self,
                  problem_text: str,
                  examples: List[Dict],
                  algorithm_sequence: List[str],
                  constraints: Dict = None) -> str:
        """
        Generate code from algorithm sequence.

        Args:
            problem_text: Problem description
            examples: List of {'input': str, 'output': str}
            algorithm_sequence: List of primitive names
            constraints: Optional constraints

        Returns:
            Python code as string
        """
        # Get primitive implementations
        primitive_code = self._get_primitive_implementations(algorithm_sequence)

        # Build prompt
        prompt = self._build_synthesis_prompt(
            problem_text,
            examples,
            algorithm_sequence,
            primitive_code,
            constraints
        )

        # Generate code based on mode
        if self.mode == "local":
            response_text = self._generate_local(prompt)
        elif self.mode == "cloud":
            response_text = self._generate_cloud(prompt)
        else:
            # Mock mode fallback
            return self._generate_mock(algorithm_sequence)

        # Extract code from response
        code = self._extract_code(response_text)
        return code

    def _generate_local(self, prompt: str) -> str:
        """Generate using local model"""
        return self.local_model.generate(prompt, temperature=0.3, max_tokens=2048)

    def _generate_cloud(self, prompt: str) -> str:
        """Generate using cloud model"""
        response = self.cloud_model.generate_content(
            prompt,
            generation_config={'temperature': 0.3, 'max_output_tokens': 2048}
        )
        return response.text

    def _generate_mock(self, algorithm_sequence: List[str]) -> str:
        """Generate template code (fallback)"""
        return f"""# Mock solution using: {', '.join(algorithm_sequence)}
n = int(input())
arr = list(map(int, input().split()))

# Process using suggested algorithms: {algorithm_sequence}
result = 0
for x in arr:
    if x % 2 == 0:  # Example logic
        result += 1

print(result)
"""

    def _get_primitive_implementations(self, algorithm_sequence: List[str]) -> str:
        """Get source code for primitives in sequence"""
        implementations = []

        for alg_name in algorithm_sequence:
            if alg_name in self.primitive_code_cache:
                implementations.append(self.primitive_code_cache[alg_name])

        return "\n\n".join(implementations)

    def _build_synthesis_prompt(self,
                                problem_text: str,
                                examples: List[Dict],
                                algorithm_sequence: List[str],
                                primitive_code: str,
                                constraints: Dict = None) -> str:
        """Build prompt for code generation"""

        examples_text = "\n".join([
            f"Input:\n{ex['input']}\nOutput:\n{ex['output']}\n"
            for ex in examples[:3]
        ])

        constraints_text = ""
        if constraints:
            constraints_text = f"\nConstraints:\n{json.dumps(constraints, indent=2)}"

        prompt = f"""You are an expert competitive programmer. Generate a complete, correct Python solution.

Problem:
{problem_text}

Examples:
{examples_text}
{constraints_text}

Suggested algorithm sequence: {algorithm_sequence}

Available primitive implementations:
{primitive_code}

Generate a complete Python solution that:
1. Reads input correctly
2. Uses the suggested algorithms
3. Produces the exact expected output
4. Handles all edge cases
5. Meets time/space constraints

Return ONLY the Python code, no explanations.

```python
"""

        return prompt

    def _extract_code(self, response_text: str) -> str:
        """Extract Python code from LLM response"""
        # Try to find code block
        code_match = re.search(r'```python\n(.*?)```', response_text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Try to find code without markers
        code_match = re.search(r'```\n(.*?)```', response_text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Return full response if no markers
        return response_text.strip()


class ProblemClassifier:
    """Classify competitive programming problems"""

    def __init__(self,
                 api_key: str = None,
                 local_model_path: str = None,
                 use_local: bool = False):
        """
        Args:
            api_key: Google API key for Gemini
            local_model_path: Path to local GGUF model
            use_local: Prefer local model
        """
        # Setup model
        self.use_local = use_local

        if use_local and local_model_path:
            self.local_model = LocalModelInference(local_model_path)
            if not self.local_model.available:
                self.use_local = False

        if not use_local and GEMINI_AVAILABLE and api_key:
            genai.configure(api_key=api_key)
            self.cloud_model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.cloud_model = None

    def classify(self, problem_text: str, examples: List[Dict] = None) -> Dict:
        """
        Classify problem and suggest algorithms.

        Returns:
            {
                'categories': List[str],
                'algorithms': List[str],
                'complexity': str,
                'constraints': Dict
            }
        """
        if self.use_local and self.local_model and self.local_model.available:
            return self._classify_local(problem_text, examples)
        elif self.cloud_model:
            return self._classify_cloud(problem_text, examples)
        else:
            return self._classify_mock(problem_text)

    def _classify_local(self, problem_text: str, examples: List[Dict]) -> Dict:
        """Classify using local model"""
        prompt = self._build_classification_prompt(problem_text, examples)
        response = self.local_model.generate(prompt, temperature=0.2, max_tokens=512)
        return self._parse_classification(response)

    def _classify_cloud(self, problem_text: str, examples: List[Dict]) -> Dict:
        """Classify using cloud model"""
        prompt = self._build_classification_prompt(problem_text, examples)
        response = self.cloud_model.generate_content(
            prompt,
            generation_config={'temperature': 0.2, 'max_output_tokens': 512}
        )
        return self._parse_classification(response.text)

    def _classify_mock(self, problem_text: str) -> Dict:
        """Mock classification (fallback)"""
        return {
            'categories': ['array', 'math'],
            'algorithms': ['use_array', 'count_if', 'find_max'],
            'complexity': 'O(n)',
            'constraints': {'n_max': 1000, 'time_limit_ms': 2000}
        }

    def _build_classification_prompt(self, problem_text: str, examples: List[Dict]) -> str:
        """Build classification prompt"""
        examples_text = ""
        if examples:
            examples_text = "\nExamples:\n" + "\n".join([
                f"Input: {ex['input'][:50]}... Output: {ex['output'][:50]}..."
                for ex in examples[:2]
            ])

        return f"""Analyze this competitive programming problem and return a JSON classification.

Problem:
{problem_text}
{examples_text}

Return JSON with these fields:
- categories: list of problem types (array, graph, dp, greedy, math, string, etc.)
- algorithms: list of 5-10 suggested primitive algorithms
- complexity: expected time complexity (e.g. "O(n)", "O(n log n)")
- constraints: dict with n_max, time_limit_ms

JSON:
"""

    def _parse_classification(self, response_text: str) -> Dict:
        """Parse classification from response"""
        try:
            # Try to extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except:
            pass

        # Fallback
        return {
            'categories': ['general'],
            'algorithms': ['use_array', 'count_if', 'find_max'],
            'complexity': 'O(n)',
            'constraints': {'n_max': 1000, 'time_limit_ms': 2000}
        }


# ============================================================================
# EXAMPLE USAGE & MODEL INSTALLATION GUIDE
# ============================================================================

if __name__ == "__main__":
    print("IOI Code Synthesizer - Local Model Support")
    print("=" * 70)

    print("\n📦 INSTALLATION GUIDE FOR LOCAL MODELS:")
    print("""
1. Install llama.cpp:
   git clone https://github.com/ggerganov/llama.cpp
   cd llama.cpp
   mkdir build && cd build
   cmake .. -DGGML_CUDA=ON  # For GPU support
   cmake --build . --config Release
   sudo cp bin/llama-cli /usr/local/bin/

2. Download a model (choose one):

   A) DeepSeek-Coder-1.3B (Recommended for Jetson):
      wget https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf

   B) Phi-3-mini (3.8B):
      wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf

   C) CodeLlama-7B (larger, may be tight on 4GB GPU):
      wget https://huggingface.co/TheBloke/CodeLlama-7B-GGUF/resolve/main/codellama-7b.Q4_K_M.gguf

3. Set model path:
   export IOI_LOCAL_MODEL="/path/to/model.gguf"
""")

    # Check if local model is configured
    model_path = os.environ.get('IOI_LOCAL_MODEL')

    if model_path and Path(model_path).exists():
        print(f"\n✅ Found local model: {model_path}")

        # Test local synthesizer
        synthesizer = IOICodeSynthesizer(
            local_model_path=model_path,
            use_local=True
        )

        # Test problem
        problem = {
            'text': "Count how many even numbers are in the array",
            'examples': [
                {'input': '5\\n2 4 6 8 10', 'output': '5'},
                {'input': '3\\n1 3 5', 'output': '0'}
            ]
        }

        print("\n🧪 Testing local model synthesis...")
        code = synthesizer.synthesize(
            problem['text'],
            problem['examples'],
            ['use_array', 'count_if']
        )

        print("\nGenerated code:")
        print("-" * 70)
        print(code)
        print("-" * 70)

    else:
        print("\n⚠️  No local model found. Set IOI_LOCAL_MODEL environment variable.")
        print("   Example: export IOI_LOCAL_MODEL=\"/home/pmc/models/deepseek-coder-1.3b.gguf\"")

        # Test mock mode
        print("\n🧪 Testing mock mode...")
        synthesizer = IOICodeSynthesizer()

        code = synthesizer.synthesize(
            "Count even numbers",
            [{'input': '5\\n2 4 6 8 10', 'output': '5'}],
            ['use_array', 'count_if']
        )

        print("\nMock generated code:")
        print("-" * 70)
        print(code)
        print("-" * 70)

    print("\n✅ Synthesizer test complete!")
