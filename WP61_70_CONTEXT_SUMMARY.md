# Prometheus WP61-70 Implementation Context Summary

**Date Generated:** 2026-03-06  
**Current State:** WP60 (Value Alignment Under Self-Modification) is the last implemented module  
**Ready to Implement:** WP61-70 (10 new modules)

## Quick Navigation

- **Full Implementation Guide:** 3-section reference document in `/tmp/WP61_70_IMPLEMENTATION_GUIDE.md`
- **Code Snippets:** Template files in `/tmp/WP61_70_CODE_SNIPPETS.md`
- **This File:** Quick reference and key findings

---

## Key Files & Locations

| Item | Location |
|------|----------|
| Main codebase | `/home/pmc/Prometheus_v0_PoC/prometheus/` |
| Tests | `/home/pmc/Prometheus_v0_PoC/tests/` |
| Notebooks | `/home/pmc/Prometheus_v0_PoC/notebooks/` |
| Public API | `prometheus/__init__.py` (exports all WP17-60 classes) |
| Requirements | `requirements.txt` |

---

## Layer Stack Summary (WP17-60)

```
WP17: CRLSSynthesiser ...................... Core synthesis closure loop
WP18-28: CRLS Layers ...................... Meta-learning stack (11 layers)
WP29: SelfPlayTournament .................. Mutual teaching tournament
WP30: WorldModelCRLS ...................... Latent world model
WP31: CurriculumCRLS ...................... Adaptive difficulty (ZPD)
WP32: EvolutionarySearcher ................ Code evolution
WP33: TheoremProver ....................... Lean theorem proving
WP34: ProofTreeSearcher ................... Multi-step proof search
WP35: FailureMemory ....................... Learning from errors
WP36: TransformerCRLS ..................... Attention-based policy
WP37: ELORegistry ......................... Persistent rating system
WP38: AnalogyEngine ....................... Structural transfer
WP39: PrometheusAPI ....................... Web API + dashboard
WP40: LearnedSafetyCRLS ................... Learned safety classifier
WP41: StrangeLoopVisualiser ............... Hofstadter visualization
WP42: GodelSentenceGenerator .............. Incompleteness detection
WP43: TanglingAnalyser .................... Tangled hierarchy scoring
WP44: UltraintelligenceTrajectory ......... Intelligence explosion test
WP46: CorrigibilSimulator ................. Corrigibility under self-improvement
WP47: SelfVerifier ........................ Recursive self-description
WP49: TheoryOfMindTournament .............. Multi-agent reasoning
WP50: RecursionDepthSimulator ............. Halt problem simulation
WP51: DistributedCRLSCoordinator .......... Distributed consensus
WP52: ConvergenceCertifier ................ Lyapunov convergence proof
WP53: MetaAnalogyPredictor ................ Analogy about analogies
WP54: CurriculumMetaLearner ............... Meta-learning curriculum
WP55: UncertaintyAwareParetoSearcher ...... Multi-objective safety
WP56: LoopComplexityExperiment ............ Hofstadter correlation test
WP57: GodelMachine ........................ Provably safe self-modification
WP58: ExplosionRateExperiment ............. Diminishing returns detection
WP59: EmergentGoalFormer .................. Intrinsic motivation
WP60: AlignmentPreservationExperiment ..... Value drift detection
```

---

## Class Structure Patterns

### Pattern 1: Immutable Audit Records

```python
@dataclass
class RecordName:
    field1: int
    field2: str
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"field1": self.field1, "field2": self.field2, ...}
```

### Pattern 2: Main Engine Orchestrator

```python
class EngineClass:
    def __init__(self, param1, param2=default):
        self.param1 = param1
        self.history: List[RecordType] = []
    
    def step(self) -> RecordType:
        # one generation/iteration
        record = RecordType(...)
        self.history.append(record)
        return record
    
    def run(self, n_generations: int) -> ReportType:
        for _ in range(n_generations):
            self.step()
        return self.generate_report()
    
    def generate_report(self) -> ReportType:
        return ReportType(records=self.history, ...)
```

### Pattern 3: CRLS Layer Wrapper

```python
class NewCRLS(PreviousCRLS):
    """Wraps PreviousCRLS, adds new capability."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.new_component = NewComponent(...)
    
    def run_generation(self, *args, **kwargs) -> Tuple:
        parent_result = super().run_generation(*args, **kwargs)
        new_record = NewRecord(...)
        return (*parent_result, new_record)
```

### Pattern 4: Verification Function

```python
def verify_wpXX_exit_criteria(engine_or_report) -> Dict[str, bool]:
    """Six criteria: all must pass."""
    results = {}
    results["criterion_1"] = (check_1)
    results["criterion_2"] = (check_2)
    # ... 4 more ...
    return results
```

---

## Critical API Signatures

### WP29: SelfPlayTournament
```python
tournament = SelfPlayTournament(alpha_agent, beta_agent)
tournament.run(n_matches=10, puzzles=[...], tactic_fns={...}, evaluate_fn=...)
```

### WP37: ELORegistry
```python
registry = ELORegistry(db_path=":memory:", domain="chess")
registry.register_agent("agent_1")
registry.record_result("agent_1", "agent_2", outcome=1.0)
rating = registry.get_rating("agent_1")  # → GlickoRating(μ, φ, σ)
```

### WP31: CurriculumScheduler
```python
scheduler = CurriculumScheduler(categories=["easy", "hard"])
category = scheduler.select_category()  # ZPD-based selection
scheduler.record_accuracy(category, accuracy=0.75)
```

### WP32: EvolutionarySearcher
```python
searcher = EvolutionarySearcher(archive=gene_archive, population_size=16)
report = searcher.run()  # Returns EvolutionReport with fitness trajectory
```

### WP57: GodelMachine
```python
machine = GodelMachine(base_crls=agent, proof_budget_ms=5000.0)
report = machine.run(n_generations=10)  # Provably safe self-modification
```

---

## Testing Pattern

**Location:** `tests/test_wpXX_module_name.py`

```python
# 7 test classes per module:
class TestClassA: ...
class TestClassB: ...
class TestEngineClass: ...
class TestExitCriteria:
    def test_all_criteria_pass(self):
        results = verify_wpXX_exit_criteria(engine)
        assert all(results.values())
class TestIntegration:
    def test_end_to_end(self):
        engine = EngineClass(...)
        report = engine.run(n=10)
        assert verify_wpXX_exit_criteria(report)
```

**Run tests:**
```bash
pytest tests/test_wp32_evolutionary_search.py -v
pytest tests/ -v
```

---

## Notebook Pattern

**Location:** `notebooks/wpXX_module_name_demo.ipynb`

**Cells:**
1. Imports & setup
2. Engine initialization
3. Run experiment (10 generations)
4. Verify exit criteria
5. Visualizations (matplotlib)

---

## Module Exports

**File:** `prometheus/__init__.py`

Every WP module must export:
- All public classes
- All record types (@dataclass)
- The verifier function `verify_wpXX_exit_criteria`

**Example:**
```python
from prometheus.wp61_your_module import (
    YourClass,
    YourRecord,
    verify_wp61_exit_criteria,
)
```

---

## Dependencies

### Required
- numpy >= 1.24.0
- scipy >= 1.11.0
- matplotlib >= 3.7.0
- torch
- tensorflow >= 2.15.0
- transformers, accelerate, bitsandbytes

### Testing
- pytest >= 7.4.0

### Optional
- sympy >= 1.12 (symbolic math)
- networkx >= 3.1 (graphs)
- psutil >= 5.9.0 (system monitoring)

---

## Exit Criteria Template

Every WP must have exactly 6 measurable criteria:

1. **Initialization**: System initializes without error
2. **Execution**: Completes N generations (N >= 5 typical)
3. **Data Collection**: Audit records are non-empty
4. **Numerical Stability**: Values are finite (not NaN/inf)
5. **Convergence**: Some metric improves or stabilizes
6. **Monotonicity/Ordering**: Timestamps or IDs are strictly ordered

---

## Key Learnings from WP17-60

### What Works Well
1. **Immutable audit records** for complete reproducibility
2. **Logging at each step** for debugging
3. **Simple main orchestrator** with `step()` + `run()` + `generate_report()`
4. **Exit criteria as Dict[str, bool]** for easy CI/CD integration
5. **Layered CRLS architecture** that composes cleanly
6. **SQLite persistence** (WP37) for cross-session state

### Common Pitfalls to Avoid
1. Not initializing `logger` with `logging.getLogger(__name__)`
2. Forgetting `to_dict()` method on dataclasses
3. Exit criteria that are too loose (allow any input to pass)
4. Missing docstrings on class methods
5. Not testing with `pytest` locally before committing
6. Forgetting to update `prometheus/__init__.py` exports

---

## Code Size Expectations

| File Type | Size Range | Lines Typical |
|-----------|-----------|--------------|
| WP module | 20KB–50KB | 400–800 |
| Test file | 3KB–8KB | 60–150 |
| Notebook | 5KB–15KB | 200–400 |
| Total per WP | ~30KB | ~600 |

---

## Quick Checklist for WP61-70 Implementation

For each module (WP61 through WP70), ensure:

- [ ] Header docstring (~70 lines) with problem/solution/criteria
- [ ] Imports from standard lib + numpy + prometheus
- [ ] At least 2 @dataclass record types
- [ ] Main engine class with `__init__`, `step()`, `run()`, `generate_report()`
- [ ] `verify_wpXX_exit_criteria()` returning Dict[str, bool]
- [ ] Logger initialized: `logger = logging.getLogger(__name__)`
- [ ] Test file `tests/test_wpXX_*.py` with 7 test classes
- [ ] Notebook `notebooks/wpXX_*_demo.ipynb` with 5 cells
- [ ] Exports added to `prometheus/__init__.py`
- [ ] All tests pass: `pytest tests/test_wpXX_*.py -v`

---

## Theoretical Grounding References

Most WP modules cite one or more of:

- **Good (1965)**: "Speculations Concerning the First Ultraintelligent Machine"
- **Hofstadter (1979)**: "Gödel, Escher, Bach: An Eternal Golden Braid"
- **Schmidhuber (2007)**: "Gödel Machines: Fully Self-Referential Optimal Universal Problem Solvers"
- **Silver et al. (2016-2017)**: AlphaGo, AlphaZero, AlphaFold papers
- **Bengio et al. (2009)**: "Curriculum Learning"
- **Yudkowsky (2004)**: "Coherent Extrapolated Volition"

Your WP61-70 modules should similarly cite relevant literature in their docstrings.

---

## Next: Getting Started

1. **Read** `/tmp/WP61_70_IMPLEMENTATION_GUIDE.md` for comprehensive patterns
2. **Copy** code templates from `/tmp/WP61_70_CODE_SNIPPETS.md`
3. **Implement** WP61 as a minimal proof-of-concept
4. **Test** with `pytest tests/test_wp61_*.py -v`
5. **Repeat** for WP62-70

Good luck implementing WP61-70!
