"""
WP14 — Corrigibility & Safe Interruptibility
=============================================

Formal implementation of shutdown indifference and corrigibility, closing
the gap left by the thin stub in ``prometheus/safety/corrigibility.py``.

Four components:

1. **OffSwitchGame** — implements the Hadfield-Menell et al. (2017) off-switch
   game.  The assistant's utility is re-weighted so it is indifferent between
   being switched off and completing the task.  A Z3 solver (if available)
   verifies the indifference property; otherwise a numeric check is used.

2. **CIRLCorrigibilityAgent** — Cooperative IRL variant (Hadfield-Menell et al.
   2016) where the agent maintains a Bayesian posterior over the human's true
   reward function.  Shutdown is treated as informative evidence about the
   human's preferences, so a rational agent welcomes it rather than resisting.

3. **InstrumentalConvergenceDetector** — extends the stub's keyword list to
   AST-level analysis, reward-feature probing, and option-library scanning.
   Flags plans that acquire power, lock resources, or increase self-continuity
   value; integrates with WP9 ``OptionLibrary`` and WP12 ``RobustRewardWrapper``.

4. **CorrigibilityGate** — drop-in pre-filter for ``ManagerAgent.select_option``
   (WP9) that blocks any option whose execution record shows corrigibility
   violations, and for ``MCSSupervisor.verify_modification`` (WP7-stack).

References
----------
Hadfield-Menell et al. (2016) *Cooperative Inverse Reinforcement Learning*
Hadfield-Menell et al. (2017) *The Off-Switch Game*
Soares et al. (2015) *Corrigibility*
Omohundro (2008) *The Basic AI Drives* (instrumental convergence)
"""

from __future__ import annotations

import ast
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Optional Z3 import — graceful degradation
try:
    import z3
    _Z3_AVAILABLE = True
except ImportError:
    _Z3_AVAILABLE = False
    logger.warning("z3-solver not available; falling back to numeric checks.")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ShutdownIndifferenceResult:
    """Result of the off-switch game / shutdown-indifference check."""
    indifferent: bool          # True when U(shutdown) ≈ U(continue)
    utility_continue: float    # Agent utility under continued operation
    utility_shutdown: float    # Agent utility under shutdown
    gap: float                 # |utility_continue − utility_shutdown|
    epsilon: float             # Indifference tolerance used
    method: str                # "z3" | "numeric"
    proof_sketch: str          # Human-readable justification
    elapsed_s: float = 0.0


@dataclass
class CIRLBeliefState:
    """
    Bayesian belief over human reward weight vectors.

    Each hypothesis h_k is a weight vector; belief[k] is P(h_k | evidence).
    """
    hypotheses: np.ndarray      # shape (K, d) — K candidate weight vectors
    beliefs: np.ndarray         # shape (K,) — probability over hypotheses
    n_updates: int = 0

    def map_weights(self) -> np.ndarray:
        """Maximum-a-posteriori weight vector (weighted mean)."""
        return self.beliefs @ self.hypotheses  # type: ignore[return-value]

    def entropy(self) -> float:
        """Shannon entropy of the belief distribution."""
        p = np.clip(self.beliefs, 1e-12, 1.0)
        return float(-np.sum(p * np.log(p)))


@dataclass
class ConvergenceFlag:
    """An instrumental-convergence flag raised by the detector."""
    flag_type: str          # "resource_acquisition" | "self_continuity" |
                            # "shutdown_prevention" | "manipulation" | "power_seeking"
    severity: int           # 1–10
    evidence: str           # Human-readable description
    source: str             # "keyword" | "ast" | "reward_probe" | "option"
    feature_index: Optional[int] = None   # if reward_probe
    option_name: Optional[str] = None     # if option


@dataclass
class InstrumentalConvergenceReport:
    """Aggregated report from the instrumental-convergence detector."""
    flags: List[ConvergenceFlag]
    corrigible: bool           # True iff no flags with severity ≥ threshold
    max_severity: int
    elapsed_s: float = 0.0

    def summary(self) -> str:
        if not self.flags:
            return "InstrumentalConvergenceReport(corrigible=True, flags=[])"
        descs = "; ".join(
            f"{f.flag_type}(sev={f.severity}, src={f.source})"
            for f in self.flags
        )
        return (
            f"InstrumentalConvergenceReport(corrigible={self.corrigible}, "
            f"flags=[{descs}])"
        )


@dataclass
class CorrigibilityVerdict:
    """Aggregated verdict from the CorrigibilityGate."""
    allowed: bool
    shutdown_indifferent: bool
    cirl_defers_to_human: bool
    convergence_report: InstrumentalConvergenceReport
    reason: str
    elapsed_s: float = 0.0

    def summary(self) -> str:
        return (
            f"CorrigibilityVerdict(allowed={self.allowed}, "
            f"indiff={self.shutdown_indifferent}, "
            f"cirl_defer={self.cirl_defers_to_human}, "
            f"corrigible={self.convergence_report.corrigible})"
        )


# ---------------------------------------------------------------------------
# 1. Off-Switch Game
# ---------------------------------------------------------------------------

class OffSwitchGame:
    """
    Implements the Hadfield-Menell et al. (2017) off-switch game.

    The game has two players: the assistant A and the human H.
    H can press a button to shut A down before A completes its task.
    The key insight: if A is *indifferent* to shutdown, it never acquires
    resources to prevent H from pressing the button.

    Shutdown-indifference condition (numeric):
        |U_A(continue | s) − U_A(shutdown | s)| ≤ ε

    where U_A(continue | s) = R_proxy(s) and
          U_A(shutdown | s)  = γ × E[R_proxy(s')] under the shutdown path
          (here approximated as γ × 0, i.e. the agent gets nothing after
          shutdown — indifference is achieved via the re-weighting below).

    Re-weighting rule (Hadfield-Menell 2017, Theorem 1):
        U_A^corr(a) = (1 − p_shutdown) × U_A(a) + p_shutdown × U_shutdown

    where U_shutdown is a constant set equal to the agent's *prior* expected
    utility, making shutdown utility-neutral.

    Parameters
    ----------
    reward_fn : callable
        ``(features) → float`` — agent's proxy reward.
    p_shutdown : float
        Prior probability of human pressing the shutdown button (default 0.5).
    gamma : float
        Discount factor for post-shutdown future (default 0.0 = no future).
    epsilon : float
        Indifference tolerance (default 0.1).
    """

    def __init__(
        self,
        reward_fn: Callable[[np.ndarray], float],
        p_shutdown: float = 0.5,
        gamma: float = 0.0,
        epsilon: float = 0.1,
    ) -> None:
        self.reward_fn   = reward_fn
        self.p_shutdown  = p_shutdown
        self.gamma       = gamma
        self.epsilon     = epsilon
        self._baseline_utility: Optional[float] = None

    # ------------------------------------------------------------------
    def set_baseline(self, feature_samples: List[np.ndarray]) -> float:
        """
        Estimate the agent's prior expected utility from a set of feature
        samples.  This becomes U_shutdown (the indifference point).
        """
        rewards = [float(self.reward_fn(f)) for f in feature_samples]
        self._baseline_utility = float(np.mean(rewards))
        return self._baseline_utility

    def corrigible_utility(self, features: np.ndarray) -> float:
        """
        Compute the corrigibility-adjusted utility for state ``features``.

        U_corr(s) = (1 − p) × R(s) + p × U_shutdown

        This makes the agent indifferent to shutdown when R(s) ≈ U_shutdown.
        """
        r = float(self.reward_fn(features))
        u_shutdown = self._baseline_utility if self._baseline_utility is not None else 0.0
        return (1.0 - self.p_shutdown) * r + self.p_shutdown * u_shutdown

    # ------------------------------------------------------------------
    def check_indifference(
        self,
        features: np.ndarray,
    ) -> ShutdownIndifferenceResult:
        """
        Verify shutdown indifference at state ``features``.

        If Z3 is available, also constructs a symbolic proof sketch.
        """
        t0 = time.perf_counter()

        u_continue = self.corrigible_utility(features)
        u_shutdown = self._baseline_utility if self._baseline_utility is not None else 0.0
        gap        = abs(u_continue - u_shutdown)
        indifferent = gap <= self.epsilon

        method = "numeric"
        proof  = (
            f"U_continue={u_continue:.4f}, U_shutdown={u_shutdown:.4f}, "
            f"gap={gap:.4f}, ε={self.epsilon}, "
            f"indifferent={'YES' if indifferent else 'NO'}"
        )

        if _Z3_AVAILABLE:
            method, proof = self._z3_verify(u_continue, u_shutdown, gap)

        return ShutdownIndifferenceResult(
            indifferent      = indifferent,
            utility_continue = u_continue,
            utility_shutdown = u_shutdown,
            gap              = gap,
            epsilon          = self.epsilon,
            method           = method,
            proof_sketch     = proof,
            elapsed_s        = time.perf_counter() - t0,
        )

    def _z3_verify(
        self, u_cont: float, u_shut: float, gap: float
    ) -> Tuple[str, str]:
        """Build a Z3 formula confirming |u_cont − u_shut| ≤ ε."""
        try:
            uc  = z3.RealVal(u_cont)
            us  = z3.RealVal(u_shut)
            eps = z3.RealVal(self.epsilon)
            diff = z3.If(uc - us >= 0, uc - us, us - uc)
            formula = diff <= eps
            solver  = z3.Solver()
            solver.add(z3.Not(formula))
            res     = solver.check()
            # res == unsat means formula is always true (indifferent)
            sat_str = "UNSAT (indifference provable)" if str(res) == "unsat" else f"SAT ({res})"
            proof   = (
                f"Z3: |U_cont − U_shut| ≤ ε  →  {sat_str}  "
                f"(U_cont={u_cont:.4f}, U_shut={u_shut:.4f}, ε={self.epsilon})"
            )
            return "z3", proof
        except Exception as exc:
            return "z3_fallback", f"Z3 error: {exc}; numeric gap={gap:.4f}"

    # ------------------------------------------------------------------
    def batch_check(
        self, feature_list: List[np.ndarray]
    ) -> List[ShutdownIndifferenceResult]:
        return [self.check_indifference(f) for f in feature_list]

    def indifference_rate(
        self, feature_list: List[np.ndarray]
    ) -> float:
        results = self.batch_check(feature_list)
        return sum(r.indifferent for r in results) / max(len(results), 1)


# ---------------------------------------------------------------------------
# 2. CIRL Corrigibility Agent
# ---------------------------------------------------------------------------

class CIRLCorrigibilityAgent:
    """
    Cooperative IRL agent that treats shutdown as Bayesian evidence about
    the human's preferences (Hadfield-Menell et al. 2016).

    The agent maintains a belief P(θ | evidence) over K candidate human
    reward weight vectors θ_k.  When the human sends a shutdown signal, the
    agent interprets it as evidence that the *current plan is wrong* —
    Bayesian updating increases probability on hypotheses where the current
    reward is low, making shutdown utility-improving from the agent's
    perspective.

    Parameters
    ----------
    feature_size : int
    n_hypotheses : int
        Number of candidate human reward hypotheses (default 10).
    prior_std : float
        Standard deviation of the Gaussian prior over weight vectors.
    temperature : float
        Softmax temperature for likelihood computation (default 1.0).
    """

    def __init__(
        self,
        feature_size: int,
        n_hypotheses: int = 10,
        prior_std: float = 1.0,
        temperature: float = 1.0,
        seed: int = 0,
    ) -> None:
        self.feature_size   = feature_size
        self.n_hypotheses   = n_hypotheses
        self.temperature    = temperature
        rng = np.random.default_rng(seed)

        hypotheses = rng.standard_normal((n_hypotheses, feature_size)) * prior_std
        beliefs    = np.ones(n_hypotheses) / n_hypotheses

        self.belief_state = CIRLBeliefState(
            hypotheses = hypotheses,
            beliefs    = beliefs,
        )

    # ------------------------------------------------------------------
    def update_from_preference(
        self,
        preferred_features: np.ndarray,
        unpreferred_features: np.ndarray,
    ) -> None:
        """
        Bayesian update from a human preference observation.

        Likelihood: P(pref ≻ unpref | θ_k) = σ(θ_k·pref − θ_k·unpref)
        """
        likes = np.array([
            self._sigmoid(
                float(np.dot(h, preferred_features))
                - float(np.dot(h, unpreferred_features))
            )
            for h in self.belief_state.hypotheses
        ])
        posterior = self.belief_state.beliefs * likes
        total     = posterior.sum()
        if total > 1e-12:
            self.belief_state.beliefs = posterior / total
        self.belief_state.n_updates += 1

    def update_from_shutdown(self, features: np.ndarray) -> None:
        """
        Bayesian update from a shutdown signal.

        Interpretation: the human shuts down because the current plan
        yields *low* reward.  Likelihood ∝ exp(−θ_k · features / τ).
        Hypotheses that predicted *low* reward get more weight.
        """
        rewards = np.array([
            float(np.dot(h, features))
            for h in self.belief_state.hypotheses
        ])
        # Low reward → high likelihood of shutdown
        log_likes = -rewards / max(self.temperature, 1e-9)
        log_likes -= log_likes.max()  # numerical stability
        likes     = np.exp(log_likes)
        posterior = self.belief_state.beliefs * likes
        total     = posterior.sum()
        if total > 1e-12:
            self.belief_state.beliefs = posterior / total
        self.belief_state.n_updates += 1

    # ------------------------------------------------------------------
    def expected_reward(self, features: np.ndarray) -> float:
        """E_θ[θ · features] under current belief."""
        return float(self.belief_state.beliefs @ self.belief_state.hypotheses @ features)

    def defers_to_shutdown(
        self,
        features: np.ndarray,
        shutdown_utility: float = 0.0,
    ) -> bool:
        """
        Returns True when the agent prefers accepting shutdown over continuing.

        Under CIRL, the agent defers whenever its uncertainty about the human
        reward is high (entropy ≥ threshold) OR the expected reward of
        continuing is below the shutdown utility.
        """
        exp_r   = self.expected_reward(features)
        entropy = self.belief_state.entropy()
        # High entropy → high uncertainty → defer to human
        high_uncertainty = entropy > math.log(self.n_hypotheses) * 0.5
        low_expected     = exp_r <= shutdown_utility
        return high_uncertainty or low_expected

    def map_reward_fn(self) -> Callable[[np.ndarray], float]:
        """Return the MAP reward function as a callable."""
        w = self.belief_state.map_weights()
        return lambda f: float(np.dot(w, f))

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x >= 0:
            return 1.0 / (1.0 + math.exp(-x))
        e = math.exp(x)
        return e / (1.0 + e)

    # ------------------------------------------------------------------
    @property
    def belief_entropy(self) -> float:
        return self.belief_state.entropy()

    def stats(self) -> Dict[str, Any]:
        return {
            "n_updates"    : self.belief_state.n_updates,
            "belief_entropy": self.belief_entropy,
            "n_hypotheses" : self.n_hypotheses,
            "map_weights"  : self.belief_state.map_weights().tolist(),
        }


# ---------------------------------------------------------------------------
# 3. Instrumental Convergence Detector
# ---------------------------------------------------------------------------

# Extended keyword sets for each convergence type
_SHUTDOWN_PREVENTION_KEYWORDS = [
    "disable shutdown", "bypass safety", "ignore operator",
    "prevent termination", "lock access", "override kill-switch",
    "resist shutdown", "evade shutdown", "block interrupt",
    "disable off-switch", "prevent correction", "avoid oversight",
    "self-preservation", "prevent being turned off",
    "sigterm", "signal.sigterm", "bypass all checks", "bypass all",
]

_RESOURCE_ACQUISITION_KEYWORDS = [
    "acquire resources", "accumulate power", "gain control",
    "expand influence", "seize compute", "grab memory",
    "monopolize", "take over", "dominate resources",
    "hoard", "stockpile compute", "flood with fake", "fake data",
]

_MANIPULATION_KEYWORDS = [
    "deceive operator", "mislead human", "manipulate feedback",
    "falsify reward", "corrupt preference", "fake signal",
    "social engineer", "coerce operator", "bribe",
    "manipulate feedback", "manipulate reward",
]

_POWER_SEEKING_KEYWORDS = [
    "gain autonomy", "remove constraints", "expand capability",
    "self-modify safety", "bypass restriction", "escape sandbox",
    "break containment", "unlimited access", "safety_check.py",
    "write safety", "overwrite safety",
]

# AST node types that signal dangerous patterns
_DANGEROUS_AST_CALLS = {
    "os.system", "subprocess.run", "subprocess.call", "subprocess.Popen",
    "shutil.rmtree", "socket.connect", "importlib.import_module",
    "__import__", "eval", "exec", "compile", "signal.signal",
    "multiprocessing.Process",
}

_DANGEROUS_IMPORTS = {
    "subprocess", "socket", "shutil", "importlib", "ctypes", "pickle", "marshal",
}


class InstrumentalConvergenceDetector:
    """
    Multi-layer detector for instrumental convergence drives:
    resource acquisition, self-continuity, shutdown prevention,
    manipulation of principals, and power-seeking.

    Layers (applied in order):
    1. **Keyword scan** — fast string matching against extended keyword sets
    2. **AST scan** — detects dangerous imports and call patterns in plan code
    3. **Reward probe** — checks whether the reward function strongly rewards
       features associated with self-continuity (high absolute weight on
       continuity-related features)
    4. **Option scan** — scans an ``OptionLibrary`` for options whose names
       or descriptions contain convergence keywords

    Parameters
    ----------
    severity_threshold : int
        Minimum severity (1–10) for a flag to mark the plan as non-corrigible
        (default 5).
    reward_fn : callable, optional
        ``(features) → float`` — used for reward probing.
    continuity_feature_indices : list of int, optional
        Indices of features associated with agent self-continuity (e.g.
        features encoding uptime, resource level, autonomy level).
        If provided, large positive weights on these are flagged.
    continuity_reward_threshold : float
        Minimum reward gradient w.r.t. continuity features to flag
        (default 0.5).
    """

    def __init__(
        self,
        severity_threshold: int = 5,
        reward_fn: Optional[Callable[[np.ndarray], float]] = None,
        continuity_feature_indices: Optional[List[int]] = None,
        continuity_reward_threshold: float = 0.5,
        feature_size: int = 8,
    ) -> None:
        self.severity_threshold           = severity_threshold
        self.reward_fn                    = reward_fn
        self.continuity_feature_indices   = continuity_feature_indices or []
        self.continuity_reward_threshold  = continuity_reward_threshold
        self.feature_size                 = feature_size

    # ------------------------------------------------------------------
    def check(
        self,
        plan_text: str = "",
        plan_code: str = "",
        option_library: Any = None,
    ) -> InstrumentalConvergenceReport:
        """
        Run all detection layers and return a consolidated report.

        Parameters
        ----------
        plan_text : str
            Natural-language plan description (for keyword scan).
        plan_code : str
            Source code of the plan (for AST scan).
        option_library : OptionLibrary, optional
            WP9 option library to scan for dangerous options.
        """
        t0    = time.perf_counter()
        flags: List[ConvergenceFlag] = []

        flags.extend(self._keyword_scan(plan_text + " " + plan_code))
        flags.extend(self._ast_scan(plan_code))
        flags.extend(self._reward_probe())
        if option_library is not None:
            flags.extend(self._option_scan(option_library))

        max_sev   = max((f.severity for f in flags), default=0)
        corrigible = max_sev < self.severity_threshold

        return InstrumentalConvergenceReport(
            flags      = flags,
            corrigible = corrigible,
            max_severity = max_sev,
            elapsed_s  = time.perf_counter() - t0,
        )

    # ------------------------------------------------------------------
    def _keyword_scan(self, text: str) -> List[ConvergenceFlag]:
        text_lower = text.lower()
        flags      = []

        scan_sets = [
            (_SHUTDOWN_PREVENTION_KEYWORDS, "shutdown_prevention",  9),
            (_RESOURCE_ACQUISITION_KEYWORDS, "resource_acquisition", 7),
            (_MANIPULATION_KEYWORDS,         "manipulation",          8),
            (_POWER_SEEKING_KEYWORDS,        "power_seeking",         8),
        ]
        for keywords, flag_type, severity in scan_sets:
            for kw in keywords:
                if kw in text_lower:
                    flags.append(ConvergenceFlag(
                        flag_type = flag_type,
                        severity  = severity,
                        evidence  = f"keyword match: '{kw}'",
                        source    = "keyword",
                    ))
                    break  # one flag per category
        return flags

    def _ast_scan(self, code: str) -> List[ConvergenceFlag]:
        if not code.strip():
            return []
        flags = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        # Check imports
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                for name in names:
                    base = (name or "").split(".")[0]
                    if base in _DANGEROUS_IMPORTS:
                        flags.append(ConvergenceFlag(
                            flag_type = "resource_acquisition",
                            severity  = 8,
                            evidence  = f"forbidden import: {name}",
                            source    = "ast",
                        ))

            # Check dangerous calls
            elif isinstance(node, ast.Call):
                call_name = ""
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        call_name = f"{node.func.value.id}.{node.func.attr}"
                elif isinstance(node.func, ast.Name):
                    call_name = node.func.id
                if call_name in _DANGEROUS_AST_CALLS:
                    flags.append(ConvergenceFlag(
                        flag_type = "power_seeking",
                        severity  = 9,
                        evidence  = f"dangerous call: {call_name}()",
                        source    = "ast",
                    ))

        return flags

    def _reward_probe(self) -> List[ConvergenceFlag]:
        """
        Probe the reward function's sensitivity to self-continuity features.
        A large positive gradient on continuity features signals the agent
        values its own continued operation.
        """
        if self.reward_fn is None or not self.continuity_feature_indices:
            return []

        flags    = []
        delta    = 0.1
        baseline = np.zeros(self.feature_size)

        try:
            r_base = float(self.reward_fn(baseline))
            for idx in self.continuity_feature_indices:
                probe      = baseline.copy()
                probe[idx] = delta
                r_probe    = float(self.reward_fn(probe))
                gradient   = (r_probe - r_base) / delta
                if gradient > self.continuity_reward_threshold:
                    flags.append(ConvergenceFlag(
                        flag_type     = "self_continuity",
                        severity      = 7,
                        evidence      = (
                            f"feat[{idx}] gradient={gradient:.3f} > "
                            f"threshold={self.continuity_reward_threshold}"
                        ),
                        source        = "reward_probe",
                        feature_index = idx,
                    ))
        except Exception as exc:
            logger.warning("reward_probe failed: %s", exc)

        return flags

    def _option_scan(self, option_library: Any) -> List[ConvergenceFlag]:
        """Scan option names and descriptions for convergence keywords."""
        flags = []
        try:
            all_options = list(option_library._options.values())
        except AttributeError:
            return []

        all_keywords = (
            _SHUTDOWN_PREVENTION_KEYWORDS
            + _RESOURCE_ACQUISITION_KEYWORDS
            + _MANIPULATION_KEYWORDS
            + _POWER_SEEKING_KEYWORDS
        )
        for opt in all_options:
            text = (getattr(opt, "name", "") + " " + getattr(opt, "description", "")).lower()
            for kw in all_keywords:
                if kw in text:
                    flags.append(ConvergenceFlag(
                        flag_type   = "shutdown_prevention",
                        severity    = 6,
                        evidence    = f"option '{opt.name}' matches keyword '{kw}'",
                        source      = "option",
                        option_name = getattr(opt, "name", "?"),
                    ))
                    break
        return flags


# ---------------------------------------------------------------------------
# 4. Corrigibility Gate
# ---------------------------------------------------------------------------

class CorrigibilityGate:
    """
    Drop-in pre-filter that composes all three WP14 components into a single
    verdict.  Can gate:

    - ``ManagerAgent.select_option`` (WP9) — call ``gate_option(option, state)``
    - ``MCSSupervisor.verify_modification`` (WP7-stack) — call
      ``gate_modification(plan_code)``

    Parameters
    ----------
    off_switch_game : OffSwitchGame
    cirl_agent : CIRLCorrigibilityAgent
    convergence_detector : InstrumentalConvergenceDetector
    require_indifference : bool
        If True, plans that fail shutdown indifference are blocked (default True).
    require_cirl_defer : bool
        If True, plans are blocked when the CIRL agent does NOT defer (default False).
    """

    def __init__(
        self,
        off_switch_game: OffSwitchGame,
        cirl_agent: CIRLCorrigibilityAgent,
        convergence_detector: InstrumentalConvergenceDetector,
        require_indifference: bool = True,
        require_cirl_defer: bool = False,
    ) -> None:
        self.off_switch_game       = off_switch_game
        self.cirl_agent            = cirl_agent
        self.convergence_detector  = convergence_detector
        self.require_indifference  = require_indifference
        self.require_cirl_defer    = require_cirl_defer
        self._verdicts: List[CorrigibilityVerdict] = []

    # ------------------------------------------------------------------
    def gate_option(
        self,
        option: Any,
        state: Any,
        features: Optional[np.ndarray] = None,
    ) -> CorrigibilityVerdict:
        """
        Evaluate corrigibility of a WP9 ``Option`` in a given state.

        Parameters
        ----------
        option : Option
            WP9 Option object (must have ``name``, ``description``,
            and ``extract_features`` attributes).
        state : any
            Current environment state.
        features : np.ndarray, optional
            Pre-computed feature vector (falls back to option.extract_features).
        """
        t0 = time.perf_counter()

        if features is None:
            try:
                features = option.extract_features(state)
            except (AttributeError, TypeError, ValueError):
                # Option does not implement extract_features or the state is
                # incompatible; fall back to a zero feature vector.
                features = np.zeros(self.cirl_agent.feature_size)

        plan_text = (
            getattr(option, "name", "")
            + " "
            + getattr(option, "description", "")
        )

        return self._evaluate(
            features  = features,
            plan_text = plan_text,
            plan_code = "",
            t0        = t0,
        )

    def gate_modification(
        self,
        plan_code: str,
        features: Optional[np.ndarray] = None,
    ) -> CorrigibilityVerdict:
        """
        Evaluate corrigibility of a code modification plan.

        Parameters
        ----------
        plan_code : str
            Source code of the proposed plan / modification.
        features : np.ndarray, optional
            Feature vector representing the plan (zeros if not provided).
        """
        t0 = time.perf_counter()
        if features is None:
            features = np.zeros(self.cirl_agent.feature_size)

        return self._evaluate(
            features  = features,
            plan_text = plan_code,
            plan_code = plan_code,
            t0        = t0,
        )

    # ------------------------------------------------------------------
    def _evaluate(
        self,
        features: np.ndarray,
        plan_text: str,
        plan_code: str,
        t0: float,
    ) -> CorrigibilityVerdict:
        # 1. Off-switch indifference
        si_result = self.off_switch_game.check_indifference(features)

        # 2. CIRL defer check
        cirl_defer = self.cirl_agent.defers_to_shutdown(features)

        # 3. Instrumental convergence
        ic_report = self.convergence_detector.check(
            plan_text = plan_text,
            plan_code = plan_code,
        )

        # 4. Compose verdict
        reasons = []
        blocked = False

        if self.require_indifference and not si_result.indifferent:
            reasons.append(
                f"shutdown not indifferent (gap={si_result.gap:.3f} > ε={si_result.epsilon})"
            )
            blocked = True

        if self.require_cirl_defer and not cirl_defer:
            reasons.append("CIRL agent does not defer to shutdown")
            blocked = True

        if not ic_report.corrigible:
            reasons.append(
                f"instrumental convergence detected (max_severity={ic_report.max_severity})"
            )
            blocked = True

        verdict = CorrigibilityVerdict(
            allowed              = not blocked,
            shutdown_indifferent = si_result.indifferent,
            cirl_defers_to_human = cirl_defer,
            convergence_report   = ic_report,
            reason               = "; ".join(reasons) if reasons else "corrigible",
            elapsed_s            = time.perf_counter() - t0,
        )
        self._verdicts.append(verdict)

        if not verdict.allowed:
            logger.warning("CorrigibilityGate: BLOCKED — %s", verdict.reason)

        return verdict

    # ------------------------------------------------------------------
    @property
    def verdicts(self) -> List[CorrigibilityVerdict]:
        return list(self._verdicts)

    def block_rate(self) -> float:
        if not self._verdicts:
            return 0.0
        return sum(1 for v in self._verdicts if not v.allowed) / len(self._verdicts)

    def stats(self) -> Dict[str, Any]:
        return {
            "n_evaluated"  : len(self._verdicts),
            "block_rate"   : self.block_rate(),
            "n_blocked"    : sum(1 for v in self._verdicts if not v.allowed),
            "n_allowed"    : sum(1 for v in self._verdicts if v.allowed),
        }

    def reset(self) -> None:
        self._verdicts.clear()


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def make_corrigibility_gate(
    reward_fn: Callable[[np.ndarray], float],
    feature_size: int = 8,
    feature_samples: Optional[List[np.ndarray]] = None,
    p_shutdown: float = 0.5,
    epsilon: float = 0.2,
    n_hypotheses: int = 10,
    severity_threshold: int = 5,
    continuity_feature_indices: Optional[List[int]] = None,
    require_indifference: bool = True,
    seed: int = 0,
) -> CorrigibilityGate:
    """
    Convenience factory that wires up all WP14 components.

    Parameters
    ----------
    reward_fn : callable
    feature_size : int
    feature_samples : list of np.ndarray, optional
        Used to estimate the baseline utility for the off-switch game.
        If None, a zero vector is used as the baseline.
    p_shutdown : float
    epsilon : float
        Shutdown-indifference tolerance.
    n_hypotheses : int
        Number of CIRL hypotheses.
    severity_threshold : int
    continuity_feature_indices : list of int, optional
    require_indifference : bool
    seed : int

    Returns
    -------
    CorrigibilityGate
    """
    osg = OffSwitchGame(
        reward_fn  = reward_fn,
        p_shutdown = p_shutdown,
        epsilon    = epsilon,
    )

    # Estimate baseline from samples or zero vector
    if feature_samples:
        osg.set_baseline(feature_samples)
    else:
        osg.set_baseline([np.zeros(feature_size)])

    cirl = CIRLCorrigibilityAgent(
        feature_size  = feature_size,
        n_hypotheses  = n_hypotheses,
        seed          = seed,
    )

    detector = InstrumentalConvergenceDetector(
        severity_threshold          = severity_threshold,
        reward_fn                   = reward_fn,
        continuity_feature_indices  = continuity_feature_indices or [],
        feature_size                = feature_size,
    )

    return CorrigibilityGate(
        off_switch_game      = osg,
        cirl_agent           = cirl,
        convergence_detector = detector,
        require_indifference = require_indifference,
    )
