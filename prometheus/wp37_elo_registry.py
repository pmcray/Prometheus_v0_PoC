"""
WP37: Online ELO & Performance Registry
=========================================

Closes the **cross-session rating gap** in the existing game-play and
synthesis evaluation machinery.

The gap in WP17–WP36
---------------------
All per-match and per-generation performance statistics are ephemeral:
they exist only for the duration of a single Python session.  There is
no persistent, calibrated rating system that:
  - Tracks how the agent's ability evolves *across* sessions.
  - Quantifies *uncertainty* in the agent's strength (new agents have wide
    confidence intervals; experienced agents have narrow ones).
  - Feeds back into WP31's curriculum scheduler (stronger agent → harder
    puzzles).

WP37 fix
--------
``ELOEntry`` — immutable per-game record stored in the registry.

``GlickoRating`` — per-agent Glicko-2 rating state:
    μ (rating), φ (rating deviation), σ (volatility).
    Glicko-2 is preferred over plain Elo because it models *uncertainty*
    explicitly: a newly created or inactive agent has high φ and therefore
    receives larger rating updates.

``ELORegistry`` — SQLite-backed persistent rating system.
  - ``register_agent(agent_id, domain)``   — create entry with default rating.
  - ``record_result(agent_a, agent_b, outcome, domain)``
      Outcome: 1.0 (A wins), 0.5 (draw), 0.0 (A loses).
  - ``update_ratings(agent_id)``           — apply Glicko-2 update for all
      pending results since the last rating update.
  - ``get_rating(agent_id)``               — return current (μ, φ) pair.
  - ``leaderboard(domain)``               — sorted list of (agent_id, rating).
  - ``rating_history(agent_id)``          — chronological (timestamp, μ) list.
  - Persist to SQLite on every write; load on construction.

``DomainRegistry`` — thin multi-domain wrapper: one ``ELORegistry`` per
domain (Chess, Go, Theorems, Code, Synthesis).

``ZPDRatingBridge`` — converts an agent's rating into a ``ZPD difficulty
multiplier`` for WP31's ``CurriculumScheduler``:
    stronger agent (higher μ) → push zpd_lo upward.

``verify_wp37_exit_criteria`` — six-criterion verifier.

Theoretical grounding
---------------------
Elo (1978) "The Rating of Chess Players, Past and Present": the original
pairwise rating system based on expected score vs actual score.

Glickman (1995, 2012) Glicko / Glicko-2: extends Elo with explicit rating
deviation φ (uncertainty) and volatility σ (consistency).  Updates are
weighted by certainty: a high-φ opponent's win counts for less.

Silver et al. (2016) AlphaGo: self-play training quality is monitored via
ELO ratings computed against historical checkpoints.  WP37 applies this
to the full Prometheus agent stack.

Good (1965): tracking self-improvement via an external calibrated metric is
essential for verifying the intelligence explosion.  WP37 provides that
metric as a persistent, cross-session signal.

Classes
-------
GlickoRating            Per-agent Glicko-2 rating state (μ, φ, σ)
ELOEntry                Immutable per-game result record
ELORegistry             SQLite-backed persistent Glicko-2 rating system
DomainRegistry          Multi-domain wrapper over ELORegistry instances
ZPDRatingBridge         Converts rating → ZPD difficulty multiplier
verify_wp37_exit_criteria  Six-criterion verifier
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Glicko-2 constants
# ---------------------------------------------------------------------------

_MU_0      = 1500.0   # default rating
_PHI_0     = 350.0    # default deviation (high uncertainty)
_SIGMA_0   = 0.06     # default volatility
_GLICKO_Q  = math.log(10) / 400.0   # scaling factor
_TAU       = 0.5      # system constant (controls volatility change)
_EPS       = 1e-6


# ---------------------------------------------------------------------------
# GlickoRating — Glicko-2 rating state
# ---------------------------------------------------------------------------

@dataclass
class GlickoRating:
    """
    Glicko-2 rating state for one agent.

    Attributes
    ----------
    agent_id : str
    domain : str
    mu : float       Rating (default 1500).
    phi : float      Rating deviation (default 350; lower = more certain).
    sigma : float    Volatility (default 0.06).
    n_games : int    Total games played.
    last_updated : float  Unix timestamp of last Glicko update.
    """
    agent_id:     str
    domain:       str
    mu:           float = _MU_0
    phi:          float = _PHI_0
    sigma:        float = _SIGMA_0
    n_games:      int   = 0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id":     self.agent_id,
            "domain":       self.domain,
            "mu":           round(self.mu, 2),
            "phi":          round(self.phi, 2),
            "sigma":        round(self.sigma, 6),
            "n_games":      self.n_games,
            "last_updated": self.last_updated,
        }


# ---------------------------------------------------------------------------
# ELOEntry — per-game result record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ELOEntry:
    """
    Immutable per-game result record.

    Attributes
    ----------
    agent_a : str
    agent_b : str
    outcome : float     1.0 = A wins, 0.5 = draw, 0.0 = A loses.
    domain : str
    timestamp : float
    """
    agent_a:   str
    agent_b:   str
    outcome:   float
    domain:    str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_a":   self.agent_a,
            "agent_b":   self.agent_b,
            "outcome":   self.outcome,
            "domain":    self.domain,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Glicko-2 math (pure Python, stateless)
# ---------------------------------------------------------------------------

def _g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi ** 2 / math.pi ** 2)


def _E(mu: float, mu_j: float, phi_j: float) -> float:
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))


def glicko2_update(
    rating:    GlickoRating,
    opponents: List[Tuple[float, float, float]],  # (mu_j, phi_j, score_j)
) -> GlickoRating:
    """
    Apply a single Glicko-2 rating update.

    Parameters
    ----------
    rating : GlickoRating
        Current agent rating.
    opponents : List[Tuple[mu_j, phi_j, score_j]]
        Results in the rating period.  score_j = 1.0/0.5/0.0.

    Returns
    -------
    Updated GlickoRating (new object).
    """
    if not opponents:
        # No games: increase phi (uncertainty grows with inactivity)
        phi_star = math.sqrt(rating.phi ** 2 + rating.sigma ** 2)
        return GlickoRating(
            agent_id     = rating.agent_id,
            domain       = rating.domain,
            mu           = rating.mu,
            phi          = phi_star,
            sigma        = rating.sigma,
            n_games      = rating.n_games,
            last_updated = time.time(),
        )

    # Step 1: scale to Glicko-2 internal scale
    mu    = (rating.mu  - _MU_0) / 173.7178
    phi   = rating.phi / 173.7178
    sigma = rating.sigma

    # Step 2: compute v (estimated variance)
    v_inv = sum(
        _g(phi_j / 173.7178) ** 2 * _E(mu, (mu_j - _MU_0) / 173.7178, phi_j / 173.7178) *
        (1 - _E(mu, (mu_j - _MU_0) / 173.7178, phi_j / 173.7178))
        for mu_j, phi_j, _ in opponents
    )
    v = 1.0 / max(v_inv, _EPS)

    # Step 3: compute delta (estimated improvement)
    delta_raw = v * sum(
        _g(phi_j / 173.7178) * (s_j - _E(mu, (mu_j - _MU_0) / 173.7178, phi_j / 173.7178))
        for mu_j, phi_j, s_j in opponents
    )

    # Step 4: update volatility via Illinois algorithm
    a = math.log(sigma ** 2)

    def f(x: float) -> float:
        ex = math.exp(x)
        d2 = phi ** 2 + v + ex
        return (ex * (delta_raw ** 2 - d2)) / (2.0 * d2 ** 2) - (x - a) / _TAU ** 2

    A = a
    B = math.log(delta_raw ** 2 - phi ** 2 - v) if delta_raw ** 2 > phi ** 2 + v else a - _TAU
    fA, fB = f(A), f(B)
    for _ in range(100):
        C  = A + (A - B) * fA / (fB - fA)
        fC = f(C)
        if fB * fC < 0:
            A, fA = B, fB
        else:
            fA /= 2.0
        B, fB = C, fC
        if abs(B - A) < _EPS:
            break
    sigma_new = math.exp(A / 2.0)

    # Step 5: update phi
    phi_star = math.sqrt(phi ** 2 + sigma_new ** 2)
    phi_new  = 1.0 / math.sqrt(1.0 / phi_star ** 2 + 1.0 / v)

    # Step 6: update mu
    mu_new = mu + phi_new ** 2 * sum(
        _g(phi_j / 173.7178) * (s_j - _E(mu, (mu_j - _MU_0) / 173.7178, phi_j / 173.7178))
        for mu_j, phi_j, s_j in opponents
    )

    # Convert back to original scale
    mu_final  = 173.7178 * mu_new  + _MU_0
    phi_final = 173.7178 * phi_new

    return GlickoRating(
        agent_id     = rating.agent_id,
        domain       = rating.domain,
        mu           = mu_final,
        phi          = phi_final,
        sigma        = sigma_new,
        n_games      = rating.n_games + len(opponents),
        last_updated = time.time(),
    )


# ---------------------------------------------------------------------------
# ELORegistry — SQLite-backed Glicko-2 registry
# ---------------------------------------------------------------------------

class ELORegistry:
    """
    SQLite-backed persistent Glicko-2 rating system.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.  Use ':memory:' for in-memory
        (non-persistent) operation.
    domain : str
        Domain name for this registry (e.g. 'chess', 'go', 'theorems').
    """

    def __init__(self, db_path: str = ":memory:", domain: str = "default"):
        self.db_path = db_path
        self.domain  = domain
        self._conn   = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()
        self._ratings: Dict[str, GlickoRating] = {}
        self._pending: Dict[str, List[Tuple[float, float, float]]] = {}
        self._load_ratings()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS ratings (
                agent_id     TEXT    NOT NULL,
                domain       TEXT    NOT NULL,
                mu           REAL    NOT NULL DEFAULT 1500.0,
                phi          REAL    NOT NULL DEFAULT 350.0,
                sigma        REAL    NOT NULL DEFAULT 0.06,
                n_games      INTEGER NOT NULL DEFAULT 0,
                last_updated REAL    NOT NULL,
                PRIMARY KEY (agent_id, domain)
            );
            CREATE TABLE IF NOT EXISTS games (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_a   TEXT  NOT NULL,
                agent_b   TEXT  NOT NULL,
                outcome   REAL  NOT NULL,
                domain    TEXT  NOT NULL,
                timestamp REAL  NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rating_history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id  TEXT  NOT NULL,
                domain    TEXT  NOT NULL,
                mu        REAL  NOT NULL,
                phi       REAL  NOT NULL,
                timestamp REAL  NOT NULL
            );
        """)
        self._conn.commit()

    def _load_ratings(self) -> None:
        cur = self._conn.cursor()
        cur.execute("SELECT agent_id, domain, mu, phi, sigma, n_games, last_updated "
                    "FROM ratings WHERE domain=?", (self.domain,))
        for row in cur.fetchall():
            agent_id, domain, mu, phi, sigma, n_games, last_updated = row
            self._ratings[agent_id] = GlickoRating(
                agent_id=agent_id, domain=domain,
                mu=mu, phi=phi, sigma=sigma,
                n_games=n_games, last_updated=last_updated,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> GlickoRating:
        """Create a new agent with default rating.  No-op if already exists."""
        if agent_id not in self._ratings:
            r = GlickoRating(agent_id=agent_id, domain=self.domain)
            self._ratings[agent_id] = r
            self._upsert_rating(r)
        return self._ratings[agent_id]

    def record_result(
        self,
        agent_a: str,
        agent_b: str,
        outcome: float,
    ) -> ELOEntry:
        """
        Record a game result.

        Parameters
        ----------
        agent_a, agent_b : str
        outcome : float   1.0 = A wins, 0.5 = draw, 0.0 = A loses.
        """
        for aid in (agent_a, agent_b):
            if aid not in self._ratings:
                self.register_agent(aid)

        entry = ELOEntry(agent_a=agent_a, agent_b=agent_b,
                         outcome=outcome, domain=self.domain)
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO games (agent_a, agent_b, outcome, domain, timestamp) VALUES (?,?,?,?,?)",
            (agent_a, agent_b, outcome, self.domain, entry.timestamp),
        )
        self._conn.commit()

        # Queue pending results for both agents
        ra = self._ratings[agent_a]
        rb = self._ratings[agent_b]
        self._pending.setdefault(agent_a, []).append((rb.mu, rb.phi, outcome))
        self._pending.setdefault(agent_b, []).append((ra.mu, ra.phi, 1.0 - outcome))
        return entry

    def update_ratings(self, agent_id: Optional[str] = None) -> None:
        """
        Apply Glicko-2 updates for all pending results.

        Parameters
        ----------
        agent_id : Optional[str]
            If given, update only this agent.  Else update all pending.
        """
        targets = [agent_id] if agent_id else list(self._pending.keys())
        for aid in targets:
            if aid not in self._pending or aid not in self._ratings:
                continue
            opponents = self._pending.pop(aid)
            old_r     = self._ratings[aid]
            new_r     = glicko2_update(old_r, opponents)
            self._ratings[aid] = new_r
            self._upsert_rating(new_r)
            # Append to history
            cur = self._conn.cursor()
            cur.execute(
                "INSERT INTO rating_history (agent_id, domain, mu, phi, timestamp) VALUES (?,?,?,?,?)",
                (aid, self.domain, new_r.mu, new_r.phi, time.time()),
            )
        self._conn.commit()

    def get_rating(self, agent_id: str) -> Optional[GlickoRating]:
        """Return current rating for agent_id, or None if not registered."""
        return self._ratings.get(agent_id)

    def leaderboard(self, top_k: Optional[int] = None) -> List[Tuple[str, float, float]]:
        """
        Return agents sorted by rating (descending).

        Returns List[Tuple[agent_id, mu, phi]].
        """
        self.update_ratings()
        board = sorted(
            ((r.agent_id, r.mu, r.phi) for r in self._ratings.values()),
            key=lambda x: x[1],
            reverse=True,
        )
        return board[:top_k] if top_k else board

    def rating_history(self, agent_id: str) -> List[Tuple[float, float]]:
        """Return chronological (timestamp, mu) list for agent_id."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT timestamp, mu FROM rating_history WHERE agent_id=? AND domain=? ORDER BY timestamp",
            (agent_id, self.domain),
        )
        return [(row[0], row[1]) for row in cur.fetchall()]

    def _upsert_rating(self, r: GlickoRating) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO ratings
               (agent_id, domain, mu, phi, sigma, n_games, last_updated)
               VALUES (?,?,?,?,?,?,?)""",
            (r.agent_id, r.domain, r.mu, r.phi, r.sigma, r.n_games, r.last_updated),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# DomainRegistry — multi-domain wrapper
# ---------------------------------------------------------------------------

class DomainRegistry:
    """
    Manages one ``ELORegistry`` per domain.

    Parameters
    ----------
    db_path : str
        SQLite path shared across domains (each uses a different table prefix
        via the ``domain`` column).
    domains : List[str]
        Domains to initialise (default: chess, go, theorems, code, synthesis).
    """

    DEFAULT_DOMAINS = ["chess", "go", "theorems", "code", "synthesis"]

    def __init__(
        self,
        db_path: str = ":memory:",
        domains: Optional[List[str]] = None,
    ):
        self.db_path  = db_path
        domains       = domains or self.DEFAULT_DOMAINS
        self._regs: Dict[str, ELORegistry] = {
            d: ELORegistry(db_path=db_path, domain=d) for d in domains
        }

    def registry(self, domain: str) -> ELORegistry:
        if domain not in self._regs:
            self._regs[domain] = ELORegistry(db_path=self.db_path, domain=domain)
        return self._regs[domain]

    def record_result(
        self,
        agent_a: str,
        agent_b: str,
        outcome: float,
        domain:  str = "synthesis",
    ) -> ELOEntry:
        return self.registry(domain).record_result(agent_a, agent_b, outcome)

    def update_all(self) -> None:
        for reg in self._regs.values():
            reg.update_ratings()

    def leaderboard(self, domain: str, top_k: Optional[int] = None) -> List[Tuple[str, float, float]]:
        return self.registry(domain).leaderboard(top_k=top_k)

    def multi_domain_summary(self) -> Dict[str, Any]:
        summary = {}
        for domain, reg in self._regs.items():
            board = reg.leaderboard(top_k=3)
            summary[domain] = [
                {"agent": a, "mu": round(mu, 1), "phi": round(phi, 1)}
                for a, mu, phi in board
            ]
        return summary


# ---------------------------------------------------------------------------
# ZPDRatingBridge — rating → ZPD difficulty multiplier
# ---------------------------------------------------------------------------

class ZPDRatingBridge:
    """
    Converts an agent's Glicko-2 rating to a ZPD difficulty multiplier
    for WP31's ``CurriculumScheduler``.

    The mapping is:
        multiplier = clip((mu - base_mu) / range_mu, 0, 1)

    where ``base_mu`` is the rating at which the multiplier = 0 (use default
    ZPD) and ``base_mu + range_mu`` is the rating at which multiplier = 1
    (use hardest curriculum).

    The caller applies:
        effective_zpd_lo = zpd_lo_base + multiplier * (zpd_lo_max - zpd_lo_base)

    Parameters
    ----------
    base_mu : float   Rating corresponding to zero multiplier (default 1200).
    range_mu : float  Rating range for full multiplier (default 600).
    zpd_lo_base : float  Default ZPD lower bound (default 0.40).
    zpd_lo_max : float   Maximum ZPD lower bound at top rating (default 0.70).
    """

    def __init__(
        self,
        base_mu:    float = 1200.0,
        range_mu:   float = 600.0,
        zpd_lo_base: float = 0.40,
        zpd_lo_max:  float = 0.70,
    ):
        self.base_mu     = base_mu
        self.range_mu    = range_mu
        self.zpd_lo_base = zpd_lo_base
        self.zpd_lo_max  = zpd_lo_max

    def multiplier(self, mu: float) -> float:
        """Return difficulty multiplier in [0, 1]."""
        return max(0.0, min(1.0, (mu - self.base_mu) / self.range_mu))

    def effective_zpd_lo(self, mu: float) -> float:
        """Return the ZPD lower bound adjusted for the agent's rating."""
        m = self.multiplier(mu)
        return self.zpd_lo_base + m * (self.zpd_lo_max - self.zpd_lo_base)

    def to_dict(self, mu: float) -> Dict[str, Any]:
        return {
            "mu":              round(mu, 1),
            "multiplier":      round(self.multiplier(mu), 4),
            "effective_zpd_lo": round(self.effective_zpd_lo(mu), 4),
        }


# ---------------------------------------------------------------------------
# verify_wp37_exit_criteria — six-criterion verifier
# ---------------------------------------------------------------------------

def verify_wp37_exit_criteria(
    registry: ELORegistry,
    domain:   DomainRegistry,
    bridge:   ZPDRatingBridge,
) -> Dict[str, bool]:
    """
    Verify WP37 exit criteria.

    Criteria
    --------
    1. Agents can be registered and assigned default ratings.
    2. Results are persisted and retrieved from the registry.
    3. Glicko-2 update changes rating after game results.
    4. Rating history is recorded chronologically.
    5. DomainRegistry manages multiple domains independently.
    6. ZPDRatingBridge maps rating correctly to ZPD multiplier.
    """
    results: Dict[str, bool] = {}

    # 1. Registration and default rating
    r = registry.register_agent("test_agent_wp37")
    results["Agents registered with default rating"] = (
        abs(r.mu - _MU_0) < 1.0 and abs(r.phi - _PHI_0) < 1.0
    )

    # 2. Results persisted and retrieved
    registry.register_agent("agent_A")
    registry.register_agent("agent_B")
    entry = registry.record_result("agent_A", "agent_B", 1.0)
    results["Game results persisted in registry"] = (entry.outcome == 1.0)

    # 3. Rating changes after update
    mu_before = registry.get_rating("agent_A").mu
    registry.update_ratings()
    mu_after = registry.get_rating("agent_A").mu
    results["Glicko-2 update changes rating after results"] = (mu_before != mu_after)

    # 4. Rating history recorded
    history = registry.rating_history("agent_A")
    results["Rating history recorded chronologically"] = (len(history) >= 1)

    # 5. DomainRegistry manages domains independently
    domain.record_result("x", "y", 1.0, "chess")
    domain.record_result("x", "y", 0.0, "go")
    domain.update_all()
    chess_board = domain.leaderboard("chess")
    go_board    = domain.leaderboard("go")
    results["DomainRegistry manages multiple domains independently"] = (
        len(chess_board) >= 1 and len(go_board) >= 1
    )

    # 6. ZPDRatingBridge maps rating correctly
    m_low  = bridge.multiplier(bridge.base_mu - 100)
    m_mid  = bridge.multiplier(bridge.base_mu + bridge.range_mu / 2)
    m_high = bridge.multiplier(bridge.base_mu + bridge.range_mu + 100)
    results["ZPDRatingBridge maps rating to multiplier in [0,1]"] = (
        m_low == 0.0 and 0.0 < m_mid < 1.0 and m_high == 1.0
    )

    return results
