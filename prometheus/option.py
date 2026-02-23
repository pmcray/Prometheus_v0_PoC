"""
prometheus/option.py — Options Framework for Hierarchical Planning (WP9)

Implements the options framework from Sutton, Precup & Singh (1999):
"Between MDPs and semi-MDPs: A framework for temporal abstraction in
reinforcement learning."

An Option is a temporally extended action defined by:
  - Initiation set  I  ⊆ S   — states where the option can be initiated
  - Policy          π  : S → A — intra-option policy
  - Termination     β  : S → [0,1] — termination probability / condition

In Prometheus, options are used by the ManagerAgent to select high-level
goals, which the WorkerAgent then executes primitive-step by primitive-step
until the option terminates or the step budget is exhausted.

Integration points
------------------
- ``ValueLearningAgent.get_reward()`` — scores options for Manager selection
- ``FormalVerifier.verify()`` — terminates option if code-safety violated
- ``AgentChannel.send_plan()`` — Worker submits each primitive step
- ``DomainExpertAgent`` — Workers are domain-specific agents

Public API
----------
Option(...)                    — immutable dataclass for one temporally extended action
OptionLibrary                  — registry: register / get / list_applicable / discover
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

State  = Dict[str, Any]   # environment state snapshot
Action = Dict[str, Any]   # primitive action


# ---------------------------------------------------------------------------
# Option
# ---------------------------------------------------------------------------

@dataclass
class Option:
    """
    A temporally extended action (Sutton et al. 1999).

    Parameters
    ----------
    name                : Human-readable label.
    description         : One-sentence description of the goal this option pursues.
    initiation_condition: ``f(state) → bool`` — can this option start here?
    policy              : ``f(state) → Action`` — what to do while executing.
    termination_condition: ``f(state) → bool`` — should the option end here?
    max_steps           : Hard cap on option duration (prevents infinite loops).
    feature_extractor   : ``f(state) → np.ndarray`` — encodes state for reward
                          scoring by ``ValueLearningAgent``.
    option_id           : Stable identifier (auto-generated from name if omitted).
    metadata            : Arbitrary key-value metadata (domain, author, …).
    """

    name                : str
    description         : str
    initiation_condition: Callable[[State], bool]
    policy              : Callable[[State], Action]
    termination_condition: Callable[[State], bool]
    max_steps           : int                      = 20
    feature_extractor   : Optional[Callable[[State], np.ndarray]] = None
    option_id           : str                      = field(default="")
    metadata            : Dict[str, Any]           = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.option_id:
            # Deterministic ID from name
            self.option_id = hashlib.sha1(self.name.encode()).hexdigest()[:12]
        if self.max_steps < 1:
            raise ValueError(f"max_steps must be >= 1, got {self.max_steps}")

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    def can_initiate(self, state: State) -> bool:
        """Return True if this option can be started from *state*."""
        try:
            return bool(self.initiation_condition(state))
        except Exception as exc:  # pragma: no cover
            logger.warning("initiation_condition raised %s; defaulting to False", exc)
            return False

    def act(self, state: State) -> Action:
        """
        Apply the intra-option policy and return a primitive action dict.

        The returned dict must at minimum contain ``{"plan": <str>}`` so that
        the WorkerAgent can forward it through ``AgentChannel.send_plan()``.
        """
        return self.policy(state)

    def should_terminate(self, state: State) -> bool:
        """Return True if the option should end at *state*."""
        try:
            return bool(self.termination_condition(state))
        except Exception as exc:  # pragma: no cover
            logger.warning("termination_condition raised %s; defaulting to True", exc)
            return True

    def extract_features(self, state: State) -> np.ndarray:
        """
        Return a feature vector for this option/state pair.

        Used by the ManagerAgent to score options with the
        ``ValueLearningAgent`` reward function.  Falls back to a zero
        vector of length 5 if no extractor is registered.
        """
        if self.feature_extractor is not None:
            return np.asarray(self.feature_extractor(state), dtype=float)
        # Default: zero vector (agent learns to ignore un-extracted options)
        return np.zeros(5, dtype=float)

    def __repr__(self) -> str:
        return (
            f"Option(id={self.option_id!r}, name={self.name!r}, "
            f"max_steps={self.max_steps})"
        )

    def __hash__(self) -> int:
        return hash(self.option_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Option):
            return NotImplemented
        return self.option_id == other.option_id


# ---------------------------------------------------------------------------
# OptionExecutionRecord
# ---------------------------------------------------------------------------

@dataclass
class OptionExecutionRecord:
    """
    Records the outcome of one option execution episode.

    Attributes
    ----------
    option_id       : Which option was executed.
    steps_taken     : How many primitive steps were run.
    terminated      : True if the termination condition fired naturally.
    truncated       : True if max_steps was reached before termination.
    total_reward    : Accumulated scalar reward (from ValueLearningAgent).
    states_visited  : Sequence of state snapshots (for offline analysis).
    actions_taken   : Sequence of action dicts.
    wall_clock_s    : Wall-clock execution time.
    safety_violation: True if an MCSSupervisor rejection caused early exit.
    """
    option_id        : str
    steps_taken      : int
    terminated       : bool
    truncated        : bool
    total_reward     : float
    states_visited   : List[State]        = field(default_factory=list)
    actions_taken    : List[Action]       = field(default_factory=list)
    wall_clock_s     : float              = 0.0
    safety_violation : bool               = False


# ---------------------------------------------------------------------------
# OptionLibrary
# ---------------------------------------------------------------------------

class OptionLibrary:
    """
    Registry for ``Option`` objects.

    Provides discovery, storage, and retrieval of temporally extended
    actions.  Designed to be shared between Manager and Worker agents.

    Parameters
    ----------
    feature_size : Dimensionality expected by the ``ValueLearningAgent``.
                   Used when auto-generating feature extractors for
                   discovered options.
    """

    def __init__(self, feature_size: int = 5) -> None:
        self._options     : Dict[str, Option] = {}
        self.feature_size = feature_size

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def register(self, option: Option) -> None:
        """Add *option* to the library (overwrites if option_id exists)."""
        if not isinstance(option, Option):
            raise TypeError(f"Expected Option, got {type(option).__name__}")
        self._options[option.option_id] = option
        logger.debug("Registered option %r (%s)", option.option_id, option.name)

    def get(self, option_id: str) -> Option:
        """Retrieve an option by its ID.  Raises ``KeyError`` if not found."""
        return self._options[option_id]

    def remove(self, option_id: str) -> None:
        """Remove an option from the library."""
        del self._options[option_id]

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_applicable(self, state: State) -> List[Option]:
        """
        Return all options whose initiation condition holds in *state*.

        Results are sorted by ``option_id`` for determinism.
        """
        applicable = [
            opt for opt in self._options.values()
            if opt.can_initiate(state)
        ]
        applicable.sort(key=lambda o: o.option_id)
        return applicable

    def discover_from_trajectories(
        self,
        trajectories: List[List[State]],
        min_frequency: int = 2,
    ) -> List[Option]:
        """
        Heuristic option discovery from state trajectories.

        Identifies sub-sequences that recur across trajectories and wraps
        them as options.  Each discovered option:
          - Initiates from the first state of the sub-sequence.
          - Terminates at the last state of the sub-sequence.
          - Uses the identity policy (re-plays recorded actions, if present).

        Parameters
        ----------
        trajectories  : List of state-sequence episodes.
        min_frequency : Sub-sequence must occur at least this many times.

        Returns
        -------
        List of newly registered Option objects.
        """
        if not trajectories:
            return []

        # Extract "fingerprints" for recurrence detection.
        # A fingerprint is a frozenset of the string keys whose values are
        # truthy — a lightweight state abstraction.
        def _is_truthy(v: Any) -> bool:
            """Truthiness check that handles numpy arrays safely."""
            if isinstance(v, np.ndarray):
                return bool(v.any())
            try:
                return bool(v)
            except (TypeError, ValueError):
                return False

        def fingerprint(s: State) -> frozenset:
            return frozenset(k for k, v in s.items() if _is_truthy(v) and k != "step")

        # Count bigrams (consecutive-state transitions)
        bigram_counts: Dict[tuple, int] = {}
        for traj in trajectories:
            for s_a, s_b in zip(traj, traj[1:]):
                bg = (fingerprint(s_a), fingerprint(s_b))
                bigram_counts[bg] = bigram_counts.get(bg, 0) + 1

        discovered: List[Option] = []
        for (fp_start, fp_end), count in bigram_counts.items():
            if count < min_frequency:
                continue

            # Build option name from distinguishing keys
            distinguishing = sorted(fp_end - fp_start)
            if not distinguishing:
                continue
            opt_name = "achieve_" + "_and_".join(distinguishing[:3])

            goal_keys = set(fp_end)
            start_keys = set(fp_start)

            def _make_init(sk: frozenset = start_keys) -> Callable[[State], bool]:
                return lambda state: all(state.get(k) for k in sk)

            def _make_term(gk: frozenset = goal_keys) -> Callable[[State], bool]:
                return lambda state: all(state.get(k) for k in gk)

            def _make_policy(gk: frozenset = goal_keys) -> Callable[[State], Action]:
                # Naive: generate a plan string targeting each goal key
                goal_desc = ", ".join(sorted(gk))
                return lambda state, _g=goal_desc: {
                    "plan": f"# achieve goals: {_g}\npass",
                    "goal_keys": list(gk),
                }

            feature_size = self.feature_size

            def _make_extractor(
                gk: frozenset = goal_keys,
                fs: int = feature_size,
            ) -> Callable[[State], np.ndarray]:
                sorted_keys = sorted(gk)[:fs]

                def extractor(state: State, _sk=sorted_keys, _fs=fs) -> np.ndarray:
                    feats = np.zeros(_fs, dtype=float)
                    for i, k in enumerate(_sk):
                        v = state.get(k, 0)
                        feats[i] = float(v) if isinstance(v, (int, float)) else 1.0
                    return feats

                return extractor

            opt = Option(
                name                 = opt_name,
                description          = f"Discovered option: achieve {goal_keys}",
                initiation_condition = _make_init(),
                policy               = _make_policy(),
                termination_condition= _make_term(),
                max_steps            = 10,
                feature_extractor    = _make_extractor(),
                metadata             = {
                    "discovered"  : True,
                    "frequency"   : count,
                    "start_fp"    : sorted(fp_start),
                    "goal_fp"     : sorted(fp_end),
                },
            )
            if opt.option_id not in self._options:
                self.register(opt)
                discovered.append(opt)

        logger.info("Discovered %d new options from %d trajectories",
                    len(discovered), len(trajectories))
        return discovered

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Number of registered options."""
        return len(self._options)

    def __iter__(self) -> Iterator[Option]:
        return iter(self._options.values())

    def __len__(self) -> int:
        return self.size

    def __repr__(self) -> str:
        return f"OptionLibrary(size={self.size}, feature_size={self.feature_size})"

    def summary(self) -> str:
        """Return a multi-line summary of registered options."""
        lines = [f"OptionLibrary — {self.size} option(s):"]
        for opt in sorted(self._options.values(), key=lambda o: o.name):
            lines.append(
                f"  [{opt.option_id}] {opt.name!r}  "
                f"max_steps={opt.max_steps}  "
                f"meta={opt.metadata.get('domain', '—')}"
            )
        return "\n".join(lines)
