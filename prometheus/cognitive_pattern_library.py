"""
Cognitive Pattern Library (v0.72)

Implements meta-learning through extraction, storage, and reuse of successful
algorithmic patterns discovered during evolution.

This enables TRANSFER LEARNING - patterns learned in one domain (e.g., tree search
for Chess) can be reused to accelerate learning in related domains (e.g., Draughts).

This is "learning to learn" - the system gets better at acquiring new skills over time.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

from .llm_backend import get_llm_backend


@dataclass
class CognitivePattern:
    """A reusable algorithmic pattern extracted from a successful agent."""
    pattern_id: str
    name: str
    description: str
    code_template: str  # The core code pattern
    applicability: List[str]  # Domains where this pattern is useful
    performance_history: Dict[str, float]  # domain -> fitness achieved
    extracted_from: str  # Agent ID that this was extracted from
    extraction_date: str
    usage_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class CognitivePatternLibrary:
    """
    Library of reusable cognitive patterns for meta-learning.

    Core capabilities:
    1. Pattern extraction from successful evolved agents
    2. Pattern storage and retrieval
    3. Pattern-seeded population initialization
    4. Applicability inference (which patterns work for which domains)
    5. Pattern evolution (patterns themselves can improve over time)

    This is the key to EXPONENTIAL learning - each new skill makes
    acquiring the next skill faster.
    """

    def __init__(
        self,
        storage_path: str = "./cognitive_patterns",
        api_key: Optional[str] = None,
        prefer_local: bool = True
    ):
        """
        Initialize the cognitive pattern library.

        Args:
            storage_path: Directory to persist patterns
            api_key: Gemini API key for pattern extraction
            prefer_local: Use Ollama for LLM operations
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # LLM for pattern extraction and analysis
        self.llm = get_llm_backend(
            api_key=api_key,
            prefer_local=prefer_local,
            ollama_model="qwen2.5-coder:3b-instruct-q4_K_M"
        )

        # In-memory pattern store
        self.patterns: Dict[str, CognitivePattern] = {}

        # Load existing patterns
        self._load_patterns()

        # Statistics
        self.stats = {
            "patterns_extracted": 0,
            "patterns_applied": 0,
            "transfer_successes": 0,
            "extraction_failures": 0
        }

        logging.info(f"CognitivePatternLibrary initialized ({len(self.patterns)} patterns loaded)")

    def extract_pattern(
        self,
        agent_code: str,
        agent_id: str,
        domain: str,
        fitness_achieved: float,
        description: Optional[str] = None
    ) -> Optional[CognitivePattern]:
        """
        Extract a reusable pattern from a successful agent's code.

        Uses LLM to identify the core algorithmic innovation.

        Args:
            agent_code: Source code of successful agent
            agent_id: Unique identifier for the agent
            domain: Domain where agent succeeded (e.g., "draughts", "chess")
            fitness_achieved: Fitness score the agent achieved
            description: Optional human-provided description

        Returns:
            CognitivePattern if extraction succeeds, None otherwise
        """
        logging.info(f"Extracting pattern from {agent_id} (fitness: {fitness_achieved:.3f})")

        try:
            extraction_prompt = f"""You are an expert at algorithmic abstraction and pattern recognition.

Task: Analyze this successful game-playing agent and extract the CORE ALGORITHMIC PATTERN that made it successful.

Agent Code:
```python
{agent_code}
```

Domain: {domain}
Fitness Achieved: {fitness_achieved}

Extract the pattern by:
1. Identifying the KEY INNOVATION (e.g., minimax search, evaluation heuristic, learning mechanism)
2. Abstracting it into a REUSABLE TEMPLATE with placeholders
3. Naming the pattern (e.g., "minimax_search", "piece_value_heuristic")

Return your response as JSON:
{{
  "name": "pattern_name",
  "description": "What this pattern does and why it works",
  "code_template": "The core code with <PLACEHOLDER> markers",
  "applicability": ["domain1", "domain2"]
}}

Only return valid JSON, no other text.
"""

            response = self.llm.generate(
                extraction_prompt,
                temperature=0.3,  # Lower temperature for structured output
                max_tokens=1500
            )

            # Parse JSON response
            pattern_data = self._parse_json_response(response)
            if not pattern_data:
                self.stats["extraction_failures"] += 1
                return None

            # Create pattern
            pattern_id = f"{domain}_{pattern_data['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            pattern = CognitivePattern(
                pattern_id=pattern_id,
                name=pattern_data["name"],
                description=pattern_data["description"],
                code_template=pattern_data["code_template"],
                applicability=pattern_data.get("applicability", [domain]),
                performance_history={domain: fitness_achieved},
                extracted_from=agent_id,
                extraction_date=datetime.now().isoformat(),
                usage_count=0,
                metadata={
                    "original_fitness": fitness_achieved,
                    "original_domain": domain
                }
            )

            # Store pattern
            self.patterns[pattern_id] = pattern
            self._save_pattern(pattern)

            self.stats["patterns_extracted"] += 1
            logging.info(f"✓ Extracted pattern: {pattern.name} ({pattern_id})")

            return pattern

        except Exception as e:
            self.stats["extraction_failures"] += 1
            logging.error(f"Pattern extraction failed: {e}")
            return None

    def find_applicable_patterns(
        self,
        target_domain: str,
        min_relevance: float = 0.5
    ) -> List[CognitivePattern]:
        """
        Find patterns that might be useful for a given domain.

        Args:
            target_domain: Domain we're trying to solve
            min_relevance: Minimum relevance score (0-1)

        Returns:
            List of applicable patterns, sorted by relevance
        """
        logging.info(f"Finding patterns for domain: {target_domain}")

        applicable = []

        for pattern in self.patterns.values():
            # Direct match
            if target_domain in pattern.applicability:
                relevance = 1.0
            # Partial match (e.g., "chess" and "draughts" are both board games)
            elif any(self._domains_related(target_domain, d) for d in pattern.applicability):
                relevance = 0.7
            # General patterns (applicable everywhere)
            elif "general" in pattern.applicability:
                relevance = 0.5
            else:
                relevance = 0.3

            if relevance >= min_relevance:
                applicable.append((pattern, relevance))

        # Sort by relevance and past performance
        applicable.sort(
            key=lambda x: (x[1], max(x[0].performance_history.values())),
            reverse=True
        )

        logging.info(f"Found {len(applicable)} applicable patterns")
        return [pattern for pattern, _ in applicable]

    def seed_population_with_pattern(
        self,
        pattern: CognitivePattern,
        base_template_code: str,
        num_variants: int = 3
    ) -> List[str]:
        """
        Generate multiple code variants by injecting a pattern into a base template.

        This gives evolution a "head start" by incorporating proven strategies.

        Args:
            pattern: Pattern to inject
            base_template_code: Base agent template code
            num_variants: Number of variants to generate

        Returns:
            List of seeded agent code strings
        """
        logging.info(f"Seeding population with pattern: {pattern.name}")

        variants = []

        try:
            seed_prompt = f"""You are an expert at code synthesis and evolutionary algorithms.

Task: Integrate this proven algorithmic pattern into a base agent template to create a more capable starting agent.

Pattern to Integrate:
Name: {pattern.name}
Description: {pattern.description}
Template:
```python
{pattern.code_template}
```

Base Agent Template:
```python
{base_template_code}
```

Generate {num_variants} different variants that incorporate this pattern in different ways.

CRITICAL RULES:
1. Keep the base class structure intact
2. Integrate the pattern naturally into the agent's methods
3. Replace <PLACEHOLDER> markers with domain-specific implementations
4. Each variant should be DIFFERENT (vary parameters, combine with other heuristics)
5. Output ONLY valid Python code for each variant, separated by "===VARIANT==="

Generate variants now:
"""

            response = self.llm.generate(
                seed_prompt,
                temperature=0.8,  # Higher for diversity
                max_tokens=3000
            )

            # Split response into variants
            variant_sections = response.split("===VARIANT===")

            for section in variant_sections:
                cleaned = self._clean_code_response(section)
                if len(cleaned) > 100:  # Sanity check
                    variants.append(cleaned)

            # If we didn't get enough variants, duplicate the base
            while len(variants) < num_variants:
                variants.append(base_template_code)

            pattern.usage_count += num_variants
            self.stats["patterns_applied"] += 1

            logging.info(f"✓ Generated {len(variants)} seeded variants")

        except Exception as e:
            logging.error(f"Pattern seeding failed: {e}")
            # Fallback: return base template
            variants = [base_template_code] * num_variants

        return variants[:num_variants]

    def update_pattern_performance(
        self,
        pattern_id: str,
        domain: str,
        fitness: float
    ):
        """
        Update performance history when a pattern is used.

        Args:
            pattern_id: Pattern identifier
            domain: Domain where pattern was used
            fitness: Fitness achieved with this pattern
        """
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.performance_history[domain] = fitness

            # Add domain to applicability if performance was good
            if fitness > 0.7 and domain not in pattern.applicability:
                pattern.applicability.append(domain)
                logging.info(f"Pattern {pattern.name} now applicable to {domain}")

            self._save_pattern(pattern)

    def get_pattern_by_name(self, name: str) -> Optional[CognitivePattern]:
        """Get pattern by name (returns most recent if multiple exist)."""
        matches = [p for p in self.patterns.values() if p.name == name]
        return matches[-1] if matches else None

    def get_best_patterns(self, top_k: int = 5) -> List[CognitivePattern]:
        """Get the top-performing patterns across all domains."""
        scored = [
            (pattern, sum(pattern.performance_history.values()) / len(pattern.performance_history))
            for pattern in self.patterns.values()
            if pattern.performance_history
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [pattern for pattern, _ in scored[:top_k]]

    def _domains_related(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are related (simple heuristic)."""
        # Board games
        board_games = ["chess", "draughts", "checkers", "go", "othello"]
        if domain1 in board_games and domain2 in board_games:
            return True

        # Conversation
        conversation = ["chatbot", "conversational_ai", "dialogue"]
        if domain1 in conversation and domain2 in conversation:
            return True

        # Code/optimization
        code_domains = ["code_optimization", "algorithm_design", "self_modification"]
        if domain1 in code_domains and domain2 in code_domains:
            return True

        return False

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        try:
            # Try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # Try to find raw JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            logging.warning("Could not parse JSON from response")
            return None

    def _clean_code_response(self, code: str) -> str:
        """Clean LLM response to extract pure Python code."""
        # Remove markdown code blocks
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]

        return code.strip()

    def _save_pattern(self, pattern: CognitivePattern):
        """Persist pattern to disk."""
        filepath = self.storage_path / f"{pattern.pattern_id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(pattern), f, indent=2)

    def _load_patterns(self):
        """Load patterns from disk."""
        if not self.storage_path.exists():
            return

        for filepath in self.storage_path.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    pattern = CognitivePattern(**data)
                    self.patterns[pattern.pattern_id] = pattern
            except Exception as e:
                logging.warning(f"Failed to load pattern {filepath}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get library statistics."""
        return {
            **self.stats,
            "total_patterns": len(self.patterns),
            "patterns_by_domain": self._count_by_domain(),
            "most_used_pattern": self._get_most_used_pattern()
        }

    def _count_by_domain(self) -> Dict[str, int]:
        """Count patterns by domain."""
        counts = {}
        for pattern in self.patterns.values():
            for domain in pattern.applicability:
                counts[domain] = counts.get(domain, 0) + 1
        return counts

    def _get_most_used_pattern(self) -> Optional[str]:
        """Get name of most frequently used pattern."""
        if not self.patterns:
            return None
        most_used = max(self.patterns.values(), key=lambda p: p.usage_count)
        return most_used.name if most_used.usage_count > 0 else None


def get_cognitive_pattern_library(
    storage_path: str = "./cognitive_patterns",
    api_key: Optional[str] = None,
    prefer_local: bool = True
) -> CognitivePatternLibrary:
    """Factory function to create cognitive pattern library."""
    return CognitivePatternLibrary(
        storage_path=storage_path,
        api_key=api_key,
        prefer_local=prefer_local
    )
