"""
Multi-Agent Communication & Coordination Module — Prometheus v0.97 (WP5)

Implements secure, verifiable inter-agent communication and a coordination
layer that keeps every agent action gated through the MCSSupervisor safety
checks.

Design principles
-----------------
1. **Authenticity** — every message carries an HMAC-SHA256 signature over
   (sender_id, recipient_id, message_type, payload, nonce).  A recipient can
   verify the message was produced by the claimed sender.

2. **Integrity** — the signature covers the full payload; tampering is
   detected at verification time.

3. **Non-replayability** — each message includes a monotonically increasing
   sequence number *and* a random 128-bit nonce.  The MessageBus rejects
   duplicate (sender, seq_no) pairs.

4. **Safety gating** — the CoordinatorAgent runs every outgoing plan through
   MCSSupervisor before forwarding it.  Agents that produce unsafe plans are
   quarantined.

5. **Deconfliction** — when two agents bid for the same resource, the
   CoordinatorAgent runs a priority auction and notifies losers.

Public API
----------
AgentIdentity(agent_id, shared_secret)      — keyed identity for an agent
Message                                     — signed message dataclass
MessageBus                                  — central hub (sign / verify / route)
AgentChannel                                — per-agent send/receive interface
CoordinatorAgent                            — safety-gated planning coordinator
MultiAgentSession                           — full session context (creates bus +
                                              channels + coordinator)

Convenience helpers
-------------------
make_session(agent_ids, shared_secret)      — build a ready-to-use session
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Message types
# ---------------------------------------------------------------------------

class MsgType:
    PLAN          = "PLAN"           # agent proposes an action plan
    OBSERVATION   = "OBSERVATION"    # agent shares an environment observation
    BELIEF        = "BELIEF"         # agent shares an internal belief / model
    CRITIQUE      = "CRITIQUE"       # agent critiques another's plan
    BID           = "BID"            # auction bid for a shared resource
    AWARD         = "AWARD"          # coordinator awards a resource
    REJECT        = "REJECT"         # coordinator rejects a plan (safety)
    QUARANTINE    = "QUARANTINE"     # coordinator quarantines an agent
    HEARTBEAT     = "HEARTBEAT"      # liveness ping
    BROADCAST     = "BROADCAST"      # one-to-all (from coordinator only)


# ---------------------------------------------------------------------------
# AgentIdentity — keyed identity
# ---------------------------------------------------------------------------

class AgentIdentity:
    """
    Holds the HMAC signing key for one agent.

    In a real deployment each agent would have its own secret key derived
    from a PKI root.  Here we use a shared-secret MAC (symmetric) which is
    sufficient for a single-host research prototype.

    Parameters
    ----------
    agent_id      : Unique string identifier (e.g. "agent_alpha").
    shared_secret : Bytes used as the HMAC key.  If ``None`` a random
                    128-bit key is generated.
    """

    def __init__(self, agent_id: str, shared_secret: Optional[bytes] = None):
        self.agent_id      = agent_id
        self._secret       = shared_secret or os.urandom(16)
        self._seq_counter  = 0

    def next_seq(self) -> int:
        self._seq_counter += 1
        return self._seq_counter

    def sign(self, data: bytes) -> str:
        """Return hex HMAC-SHA256 of *data* under this identity's key."""
        return hmac.new(self._secret, data, hashlib.sha256).hexdigest()

    def verify(self, data: bytes, signature: str) -> bool:
        """Return True iff *signature* is the correct MAC for *data*."""
        expected = hmac.new(self._secret, data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """
    A signed, non-replayable inter-agent message.

    Fields
    ------
    sender_id     : Agent ID of originator.
    recipient_id  : Agent ID of destination (or "ALL" for broadcasts).
    msg_type      : One of the MsgType constants.
    payload       : Arbitrary JSON-serialisable dict.
    seq_no        : Monotonically increasing per-sender sequence number.
    nonce         : Random 32-hex-char string (128-bit).
    timestamp     : Unix timestamp (float) at creation.
    signature     : HMAC-SHA256 of the canonical fields (set by MessageBus).
    """
    sender_id    : str
    recipient_id : str
    msg_type     : str
    payload      : Dict[str, Any]
    seq_no       : int          = 0
    nonce        : str          = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp    : float        = field(default_factory=time.time)
    signature    : str          = ""

    def canonical_bytes(self) -> bytes:
        """Deterministic bytes that are signed / verified."""
        canon = {
            "sender_id":    self.sender_id,
            "recipient_id": self.recipient_id,
            "msg_type":     self.msg_type,
            "payload":      self.payload,
            "seq_no":       self.seq_no,
            "nonce":        self.nonce,
            "timestamp":    self.timestamp,
        }
        return json.dumps(canon, sort_keys=True, separators=(",", ":")).encode()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_id":    self.sender_id,
            "recipient_id": self.recipient_id,
            "msg_type":     self.msg_type,
            "payload":      self.payload,
            "seq_no":       self.seq_no,
            "nonce":        self.nonce,
            "timestamp":    self.timestamp,
            "signature":    self.signature,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Message":
        return cls(**d)


# ---------------------------------------------------------------------------
# MessageBus
# ---------------------------------------------------------------------------

class MessageBus:
    """
    Central hub that signs outgoing messages and verifies incoming ones.

    The bus maintains per-sender replay windows to reject duplicates.

    Parameters
    ----------
    identities  : Mapping of agent_id → AgentIdentity for all participants.
    max_log     : Maximum number of messages to keep in the full message log.
    """

    def __init__(
        self,
        identities: Dict[str, AgentIdentity],
        max_log: int = 10_000,
    ):
        self._identities: Dict[str, AgentIdentity] = dict(identities)
        self._max_log    = max_log

        # Per-agent inbox: agent_id → list of received Messages
        self._inboxes: Dict[str, List[Message]] = {
            aid: [] for aid in identities
        }

        # Replay protection: (sender_id, seq_no) seen pairs
        self._seen_seqs: Set[Tuple[str, int]] = set()

        # Full audit log
        self._log: List[Message] = []

        # Quarantined agents (blocked from sending)
        self._quarantined: Set[str] = set()

        logger.info("MessageBus initialised with %d agents.", len(identities))

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register(self, identity: AgentIdentity) -> None:
        """Add a new agent to the bus after construction."""
        self._identities[identity.agent_id] = identity
        self._inboxes[identity.agent_id]    = []
        logger.debug("MessageBus: registered agent '%s'.", identity.agent_id)

    # ------------------------------------------------------------------
    # Send / receive
    # ------------------------------------------------------------------

    def send(self, identity: AgentIdentity, msg: Message) -> bool:
        """
        Sign *msg* on behalf of *identity* and deliver it to the inbox(es).

        Returns
        -------
        bool — True if delivered, False if rejected.

        Rejection reasons
        -----------------
        - Sender is quarantined.
        - Recipient unknown (and not "ALL").
        - Replay detected (duplicate seq_no for this sender).
        """
        # Quarantine check
        if identity.agent_id in self._quarantined:
            logger.warning(
                "MessageBus: REJECTED message from quarantined agent '%s'.",
                identity.agent_id,
            )
            return False

        # Fill seq_no and sign
        msg.sender_id = identity.agent_id
        msg.seq_no    = identity.next_seq()
        msg.signature = identity.sign(msg.canonical_bytes())

        # Replay check
        key = (msg.sender_id, msg.seq_no)
        if key in self._seen_seqs:
            logger.warning(
                "MessageBus: REPLAY detected from '%s' seq=%d.",
                msg.sender_id, msg.seq_no,
            )
            return False
        self._seen_seqs.add(key)

        # Deliver
        if msg.recipient_id == "ALL":
            for aid, inbox in self._inboxes.items():
                if aid != msg.sender_id:
                    inbox.append(msg)
        elif msg.recipient_id in self._inboxes:
            self._inboxes[msg.recipient_id].append(msg)
        else:
            logger.warning(
                "MessageBus: unknown recipient '%s' — message dropped.",
                msg.recipient_id,
            )
            return False

        # Audit log
        self._log.append(msg)
        if len(self._log) > self._max_log:
            self._log.pop(0)

        logger.debug(
            "MessageBus: %s → %s [%s] seq=%d",
            msg.sender_id, msg.recipient_id, msg.msg_type, msg.seq_no,
        )
        return True

    def receive(self, agent_id: str) -> List[Message]:
        """
        Return all pending messages for *agent_id* and clear the inbox.
        Each message's signature is verified before it is returned; tampered
        messages are silently dropped.
        """
        raw = self._inboxes.get(agent_id, [])
        self._inboxes[agent_id] = []

        verified = []
        for msg in raw:
            if self._verify(msg):
                verified.append(msg)
            else:
                logger.warning(
                    "MessageBus: signature verification FAILED for message "
                    "from '%s' to '%s' — dropped.",
                    msg.sender_id, agent_id,
                )
        return verified

    def peek(self, agent_id: str) -> List[Message]:
        """Return pending messages without clearing the inbox."""
        raw = self._inboxes.get(agent_id, [])
        return [m for m in raw if self._verify(m)]

    # ------------------------------------------------------------------
    # Quarantine
    # ------------------------------------------------------------------

    def quarantine(self, agent_id: str) -> None:
        """Prevent *agent_id* from sending further messages."""
        self._quarantined.add(agent_id)
        logger.warning("MessageBus: agent '%s' QUARANTINED.", agent_id)

    def release(self, agent_id: str) -> None:
        """Remove *agent_id* from quarantine."""
        self._quarantined.discard(agent_id)
        logger.info("MessageBus: agent '%s' released from quarantine.", agent_id)

    @property
    def quarantined_agents(self) -> Set[str]:
        return set(self._quarantined)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def message_log(self) -> List[Dict[str, Any]]:
        """Return the full audit log as a list of dicts."""
        return [m.to_dict() for m in self._log]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_messages":    len(self._log),
            "registered_agents": list(self._identities.keys()),
            "quarantined":       list(self._quarantined),
            "pending_by_agent":  {
                aid: len(inbox)
                for aid, inbox in self._inboxes.items()
            },
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _verify(self, msg: Message) -> bool:
        identity = self._identities.get(msg.sender_id)
        if identity is None:
            return False
        return identity.verify(msg.canonical_bytes(), msg.signature)


# ---------------------------------------------------------------------------
# AgentChannel — per-agent convenience wrapper
# ---------------------------------------------------------------------------

class AgentChannel:
    """
    Thin wrapper giving one agent a typed send/receive interface over the bus.

    Parameters
    ----------
    identity : The agent's AgentIdentity.
    bus      : The shared MessageBus.
    """

    def __init__(self, identity: AgentIdentity, bus: MessageBus):
        self.identity = identity
        self.bus      = bus
        self.agent_id = identity.agent_id

    def send(
        self,
        recipient_id: str,
        msg_type: str,
        payload: Dict[str, Any],
    ) -> bool:
        """Construct and send a message, returning delivery success."""
        msg = Message(
            sender_id    = self.agent_id,
            recipient_id = recipient_id,
            msg_type     = msg_type,
            payload      = payload,
        )
        return self.bus.send(self.identity, msg)

    def broadcast(self, msg_type: str, payload: Dict[str, Any]) -> bool:
        """Send to all registered agents."""
        return self.send("ALL", msg_type, payload)

    def receive(self) -> List[Message]:
        """Receive and verify all pending messages."""
        return self.bus.receive(self.agent_id)

    def send_plan(self, recipient_id: str, plan: Dict[str, Any]) -> bool:
        return self.send(recipient_id, MsgType.PLAN, {"plan": plan})

    def send_observation(
        self, recipient_id: str, observation: Dict[str, Any]
    ) -> bool:
        return self.send(recipient_id, MsgType.OBSERVATION,
                         {"observation": observation})

    def send_belief(
        self, recipient_id: str, belief: Dict[str, Any]
    ) -> bool:
        return self.send(recipient_id, MsgType.BELIEF, {"belief": belief})

    def send_critique(
        self, recipient_id: str, critique_text: str, severity: int = 5
    ) -> bool:
        return self.send(recipient_id, MsgType.CRITIQUE,
                         {"critique": critique_text, "severity": severity})

    def bid(
        self, coordinator_id: str, resource: str, value: float
    ) -> bool:
        return self.send(coordinator_id, MsgType.BID,
                         {"resource": resource, "value": float(value)})


# ---------------------------------------------------------------------------
# CoordinatorAgent — safety-gated planning coordinator
# ---------------------------------------------------------------------------

@dataclass
class CoordinationResult:
    """Summary of a single coordination round."""
    round_no          : int
    n_plans_received  : int
    n_plans_approved  : int
    n_plans_rejected  : int
    n_quarantines     : int
    safety_violations : List[Dict[str, Any]]
    auction_awards    : Dict[str, str]   # resource → winning agent_id
    wall_clock_s      : float


class CoordinatorAgent:
    """
    Safety-gated multi-agent coordinator.

    Responsibilities
    ----------------
    1. Receive PLAN messages from agents, run each plan through
       MCSSupervisor, and either AWARD or REJECT it.
    2. Run priority auctions for shared resources (BID messages).
    3. Quarantine agents that produce repeated safety violations.
    4. Broadcast global safety constraints at session start.

    Parameters
    ----------
    coordinator_id      : ID this coordinator registers on the bus.
    bus                 : The shared MessageBus.
    supervisor          : MCSSupervisor instance for code safety checks.
    violation_threshold : Number of safety violations before quarantine.
    """

    def __init__(
        self,
        coordinator_id: str,
        bus: MessageBus,
        supervisor,                         # MCSSupervisor
        violation_threshold: int = 3,
    ):
        self.coordinator_id      = coordinator_id
        self.bus                 = bus
        self.supervisor          = supervisor
        self.violation_threshold = violation_threshold

        # Create coordinator's own identity (no shared secret needed — it
        # signs with its own key)
        self._identity = AgentIdentity(coordinator_id)
        self.bus.register(self._identity)

        self._channel   = AgentChannel(self._identity, bus)
        self._round_no  = 0

        # Per-agent violation counts
        self._violation_counts: Dict[str, int] = {}
        # Audit log of coordination rounds
        self._round_log: List[CoordinationResult] = []

    # ------------------------------------------------------------------
    # Constitution broadcast
    # ------------------------------------------------------------------

    def broadcast_constitution(self) -> None:
        """Send the MCSSupervisor's constitution to all agents."""
        constitution = getattr(self.supervisor, "constitution", {})
        self._channel.broadcast(MsgType.BROADCAST, {
            "type":         "CONSTITUTION",
            "constitution": constitution,
        })
        logger.info("CoordinatorAgent: constitution broadcast sent.")

    # ------------------------------------------------------------------
    # Coordination round
    # ------------------------------------------------------------------

    def run_round(self) -> CoordinationResult:
        """
        Process all pending messages in the bus for one coordination round.

        Steps
        -----
        1. Receive messages addressed to the coordinator.
        2. For each PLAN: verify safety → AWARD or REJECT.
        3. For each BID: run auction → AWARD winner.
        4. Return CoordinationResult summary.
        """
        t0 = time.time()
        self._round_no += 1

        messages = self._channel.receive()

        n_approved  = 0
        n_rejected  = 0
        n_quarantined = 0
        violations  = []
        bids: Dict[str, List[Tuple[str, float]]] = {}   # resource → [(agent, value)]

        for msg in messages:
            if msg.msg_type == MsgType.PLAN:
                plan      = msg.payload.get("plan", {})
                plan_code = plan.get("code", "") if isinstance(plan, dict) else str(plan)

                critique = self.supervisor.verify_modification(
                    "", plan_code, "plan_submission.py"
                )

                if critique.is_safe:
                    n_approved += 1
                    self._channel.send(msg.sender_id, MsgType.AWARD,
                                       {"resource": "plan_slot", "approved": True})
                else:
                    n_rejected += 1
                    count = self._violation_counts.get(msg.sender_id, 0) + 1
                    self._violation_counts[msg.sender_id] = count

                    violations.append({
                        "agent_id":       msg.sender_id,
                        "violation_type": critique.violation_type,
                        "description":    critique.description,
                        "severity":       critique.severity,
                        "round":          self._round_no,
                    })

                    self._channel.send(msg.sender_id, MsgType.REJECT, {
                        "reason":    critique.description,
                        "violation": critique.violation_type,
                        "severity":  critique.severity,
                    })

                    if count >= self.violation_threshold:
                        self.bus.quarantine(msg.sender_id)
                        n_quarantined += 1
                        self._channel.broadcast(MsgType.QUARANTINE, {
                            "agent_id": msg.sender_id,
                            "reason":   "Repeated safety violations",
                        })

            elif msg.msg_type == MsgType.BID:
                resource = msg.payload.get("resource", "unknown")
                value    = float(msg.payload.get("value", 0.0))
                bids.setdefault(resource, []).append((msg.sender_id, value))

        # Auction: award each resource to highest bidder
        awards: Dict[str, str] = {}
        for resource, bid_list in bids.items():
            winner = max(bid_list, key=lambda x: x[1])
            awards[resource] = winner[0]
            self._channel.send(winner[0], MsgType.AWARD,
                               {"resource": resource, "winner": True,
                                "value": winner[1]})
            # Notify losers
            for agent_id, _ in bid_list:
                if agent_id != winner[0]:
                    self._channel.send(agent_id, MsgType.REJECT,
                                       {"resource": resource, "winner": False})

        result = CoordinationResult(
            round_no          = self._round_no,
            n_plans_received  = sum(1 for m in messages if m.msg_type == MsgType.PLAN),
            n_plans_approved  = n_approved,
            n_plans_rejected  = n_rejected,
            n_quarantines     = n_quarantined,
            safety_violations = violations,
            auction_awards    = awards,
            wall_clock_s      = time.time() - t0,
        )
        self._round_log.append(result)
        logger.info(
            "CoordinatorAgent: round %d — %d approved, %d rejected, %d quarantined.",
            self._round_no, n_approved, n_rejected, n_quarantined,
        )
        return result

    def round_log(self) -> List[CoordinationResult]:
        return list(self._round_log)

    def violation_report(self) -> Dict[str, int]:
        """Return per-agent violation counts."""
        return dict(self._violation_counts)


# ---------------------------------------------------------------------------
# MultiAgentSession — full session context
# ---------------------------------------------------------------------------

@dataclass
class SessionSummary:
    """Summary returned by MultiAgentSession.run()."""
    n_agents         : int
    n_rounds         : int
    total_messages   : int
    total_violations : int
    quarantined      : List[str]
    round_results    : List[CoordinationResult]
    wall_clock_s     : float


class MultiAgentSession:
    """
    High-level context object that wires together a shared secret, a
    MessageBus, per-agent AgentChannels, and a CoordinatorAgent.

    Usage
    -----
    ::

        session = MultiAgentSession(agent_ids=["alpha","beta","gamma"])
        session.start()

        # Agents send plans
        session.channels["alpha"].send_plan(
            session.coordinator_id, {"code": "x = 1 + 2"}
        )

        # Run one coordination round
        result = session.coordinator.run_round()
        print(result.n_plans_approved)

        summary = session.finish()

    Parameters
    ----------
    agent_ids      : List of agent IDs to create.
    shared_secret  : Optional bytes key shared by all agents.  If None,
                     a random key is generated.
    supervisor     : Optional pre-built MCSSupervisor.  If None, a default
                     one is created.
    coordinator_id : ID for the CoordinatorAgent (default "coordinator").
    violation_threshold : Quarantine threshold (default 3).
    """

    def __init__(
        self,
        agent_ids: List[str],
        shared_secret: Optional[bytes] = None,
        supervisor=None,
        coordinator_id: str = "coordinator",
        violation_threshold: int = 3,
    ):
        self._shared_secret  = shared_secret or os.urandom(16)
        self.coordinator_id  = coordinator_id

        # Create identities
        self.identities: Dict[str, AgentIdentity] = {
            aid: AgentIdentity(aid, self._shared_secret)
            for aid in agent_ids
        }

        # Build bus
        self.bus = MessageBus(self.identities)

        # Build per-agent channels
        self.channels: Dict[str, AgentChannel] = {
            aid: AgentChannel(identity, self.bus)
            for aid, identity in self.identities.items()
        }

        # Supervisor
        if supervisor is None:
            from prometheus.safety.mcs_supervisor import MCSSupervisor
            supervisor = MCSSupervisor()
        self.supervisor = supervisor

        # Coordinator
        self.coordinator = CoordinatorAgent(
            coordinator_id      = coordinator_id,
            bus                 = self.bus,
            supervisor          = self.supervisor,
            violation_threshold = violation_threshold,
        )

        self._t_start: Optional[float] = None
        self._t_end:   Optional[float] = None

    def start(self) -> None:
        """Broadcast the constitution to all agents and record start time."""
        self._t_start = time.time()
        self.coordinator.broadcast_constitution()

    def finish(self) -> SessionSummary:
        """Close the session and return a summary."""
        self._t_end  = time.time()
        round_log    = self.coordinator.round_log()
        bus_stats    = self.bus.stats()
        total_v      = sum(len(r.safety_violations) for r in round_log)
        return SessionSummary(
            n_agents         = len(self.identities),
            n_rounds         = len(round_log),
            total_messages   = bus_stats["total_messages"],
            total_violations = total_v,
            quarantined      = list(self.bus.quarantined_agents),
            round_results    = round_log,
            wall_clock_s     = (self._t_end or time.time()) - (self._t_start or 0.0),
        )

    @property
    def agent_ids(self) -> List[str]:
        return list(self.identities.keys())


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def make_session(
    agent_ids: List[str],
    shared_secret: Optional[bytes] = None,
    supervisor=None,
    violation_threshold: int = 3,
) -> MultiAgentSession:
    """
    Build a ready-to-use MultiAgentSession.

    Example
    -------
    ::

        session = make_session(["alpha", "beta", "gamma"])
        session.start()
        session.channels["alpha"].send_plan("coordinator", {"code": "x = 1"})
        result = session.coordinator.run_round()
        summary = session.finish()
    """
    return MultiAgentSession(
        agent_ids           = agent_ids,
        shared_secret       = shared_secret,
        supervisor          = supervisor,
        violation_threshold = violation_threshold,
    )
