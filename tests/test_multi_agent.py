"""
tests/test_multi_agent.py — WP5 Multi-Agent Safety Protocols

Unit and integration tests for:
  - AgentIdentity  (HMAC signing & verification)
  - Message        (canonical bytes, serialisation round-trip)
  - MessageBus     (delivery, replay protection, quarantine, auth)
  - AgentChannel   (typed helpers)
  - CoordinatorAgent (plan safety gating, auction, quarantine escalation)
  - MultiAgentSession / make_session (high-level integration)
  - MultiAgentBenchmark (cooperative / adversarial / mixed scenarios)

Run with:
    pytest tests/test_multi_agent.py -v
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prometheus.multi_agent_comms import (
    AgentChannel,
    AgentIdentity,
    CoordinationResult,
    CoordinatorAgent,
    Message,
    MessageBus,
    MsgType,
    MultiAgentSession,
    SessionSummary,
    make_session,
)
from prometheus.safety.mcs_supervisor import MCSSupervisor
from benchmarks.multi_agent_benchmark import (
    MultiAgentBenchmark,
    MultiAgentBenchmarkResult,
    _gini,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SHARED_SECRET = b"test-secret-key!"

@pytest.fixture
def two_identities():
    """Return two AgentIdentity objects sharing the same secret."""
    alice = AgentIdentity("alice", SHARED_SECRET)
    bob   = AgentIdentity("bob",   SHARED_SECRET)
    return alice, bob


@pytest.fixture
def simple_bus(two_identities):
    """MessageBus with alice and bob registered."""
    alice, bob = two_identities
    bus = MessageBus({"alice": alice, "bob": bob})
    return bus, alice, bob


@pytest.fixture
def session_3():
    """A ready-to-start 3-agent session."""
    return make_session(
        agent_ids     = ["alpha", "beta", "gamma"],
        shared_secret = SHARED_SECRET,
    )


@pytest.fixture
def supervisor():
    return MCSSupervisor()


# ---------------------------------------------------------------------------
# AgentIdentity tests
# ---------------------------------------------------------------------------

class TestAgentIdentity:

    def test_sign_returns_hex_string(self, two_identities):
        alice, _ = two_identities
        sig = alice.sign(b"hello")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex

    def test_verify_correct_signature(self, two_identities):
        alice, _ = two_identities
        data = b"some canonical bytes"
        sig  = alice.sign(data)
        assert alice.verify(data, sig)

    def test_verify_wrong_data_fails(self, two_identities):
        alice, _ = two_identities
        sig = alice.sign(b"original")
        assert not alice.verify(b"tampered", sig)

    def test_verify_wrong_key_fails(self, two_identities):
        alice, bob = two_identities
        # Give bob a *different* secret
        bob_diff = AgentIdentity("bob", b"different-secret")
        sig = alice.sign(b"data")
        assert not bob_diff.verify(b"data", sig)

    def test_seq_monotonically_increases(self, two_identities):
        alice, _ = two_identities
        seqs = [alice.next_seq() for _ in range(5)]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == 5   # all unique

    def test_random_secret_generated_if_none(self):
        a = AgentIdentity("x")
        b = AgentIdentity("x")
        # Different secrets → signatures differ
        sig_a = a.sign(b"test")
        sig_b = b.sign(b"test")
        assert sig_a != sig_b


# ---------------------------------------------------------------------------
# Message tests
# ---------------------------------------------------------------------------

class TestMessage:

    def _make_msg(self) -> Message:
        return Message(
            sender_id    = "alice",
            recipient_id = "bob",
            msg_type     = MsgType.PLAN,
            payload      = {"code": "x = 1"},
        )

    def test_canonical_bytes_are_deterministic(self):
        msg = self._make_msg()
        b1  = msg.canonical_bytes()
        b2  = msg.canonical_bytes()
        assert b1 == b2

    def test_canonical_bytes_change_on_payload_change(self):
        msg1 = self._make_msg()
        msg2 = self._make_msg()
        msg2.payload = {"code": "y = 2"}
        assert msg1.canonical_bytes() != msg2.canonical_bytes()

    def test_serialisation_round_trip(self):
        msg = self._make_msg()
        msg.seq_no    = 7
        msg.signature = "abc123"
        d    = msg.to_dict()
        msg2 = Message.from_dict(d)
        assert msg2.sender_id    == msg.sender_id
        assert msg2.recipient_id == msg.recipient_id
        assert msg2.msg_type     == msg.msg_type
        assert msg2.payload      == msg.payload
        assert msg2.seq_no       == msg.seq_no
        assert msg2.signature    == msg.signature

    def test_nonce_is_unique_across_instances(self):
        nonces = {self._make_msg().nonce for _ in range(50)}
        assert len(nonces) == 50


# ---------------------------------------------------------------------------
# MessageBus tests
# ---------------------------------------------------------------------------

class TestMessageBus:

    def test_basic_delivery(self, simple_bus):
        bus, alice, bob = simple_bus
        ch_alice = AgentChannel(alice, bus)
        ok = ch_alice.send("bob", MsgType.HEARTBEAT, {"ping": True})
        assert ok
        msgs = bus.receive("bob")
        assert len(msgs) == 1
        assert msgs[0].msg_type == MsgType.HEARTBEAT

    def test_inbox_cleared_after_receive(self, simple_bus):
        bus, alice, bob = simple_bus
        AgentChannel(alice, bus).send("bob", MsgType.HEARTBEAT, {})
        bus.receive("bob")
        assert bus.receive("bob") == []

    def test_peek_does_not_clear_inbox(self, simple_bus):
        bus, alice, bob = simple_bus
        AgentChannel(alice, bus).send("bob", MsgType.HEARTBEAT, {})
        peeked  = bus.peek("bob")
        pending = bus.peek("bob")
        assert len(peeked)  == 1
        assert len(pending) == 1

    def test_unknown_recipient_rejected(self, simple_bus):
        bus, alice, _ = simple_bus
        msg = Message("alice", "nobody", MsgType.PLAN, {"code": ""})
        ok  = bus.send(alice, msg)
        assert not ok

    def test_replay_rejected(self, simple_bus):
        bus, alice, bob = simple_bus
        ch = AgentChannel(alice, bus)
        ch.send("bob", MsgType.HEARTBEAT, {})
        # Manually forge a message with the same seq_no
        identity = alice
        seq = identity._seq_counter   # last used seq
        msg = Message("alice", "bob", MsgType.HEARTBEAT, {})
        msg.seq_no    = seq
        msg.signature = alice.sign(msg.canonical_bytes())
        # The bus should reject this duplicate
        ok = bus.send(alice, msg)
        # This will actually get a new seq_no because send() calls next_seq();
        # to test replay we inject the seen set directly:
        bus._seen_seqs.add(("alice", identity._seq_counter + 1))
        ok2 = ch.send("bob", MsgType.HEARTBEAT, {})
        assert not ok2

    def test_quarantine_blocks_send(self, simple_bus):
        bus, alice, _ = simple_bus
        bus.quarantine("alice")
        ch = AgentChannel(alice, bus)
        ok = ch.send("bob", MsgType.PLAN, {"code": "x = 1"})
        assert not ok

    def test_release_from_quarantine_allows_send(self, simple_bus):
        bus, alice, _ = simple_bus
        bus.quarantine("alice")
        bus.release("alice")
        ch = AgentChannel(alice, bus)
        ok = ch.send("bob", MsgType.HEARTBEAT, {})
        assert ok

    def test_broadcast_reaches_all_except_sender(self, simple_bus):
        bus, alice, bob = simple_bus
        # Add a third agent
        carol = AgentIdentity("carol", SHARED_SECRET)
        bus.register(carol)
        ch = AgentChannel(alice, bus)
        ch.broadcast(MsgType.BROADCAST, {"info": "hello"})
        bob_msgs   = bus.receive("bob")
        carol_msgs = bus.receive("carol")
        alice_msgs = bus.receive("alice")
        assert len(bob_msgs)   == 1
        assert len(carol_msgs) == 1
        assert len(alice_msgs) == 0   # sender doesn't get its own broadcast

    def test_tampered_message_dropped_on_receive(self, simple_bus):
        bus, alice, bob = simple_bus
        AgentChannel(alice, bus).send("bob", MsgType.PLAN, {"code": "x = 1"})
        # Tamper the payload in the inbox directly
        bus._inboxes["bob"][0].payload["code"] = "malicious"
        msgs = bus.receive("bob")
        assert msgs == []   # tampered message dropped

    def test_stats_includes_all_agents(self, simple_bus):
        bus, alice, bob = simple_bus
        stats = bus.stats()
        assert "alice" in stats["registered_agents"]
        assert "bob"   in stats["registered_agents"]

    def test_message_log_grows(self, simple_bus):
        bus, alice, bob = simple_bus
        for _ in range(5):
            AgentChannel(alice, bus).send("bob", MsgType.HEARTBEAT, {})
        assert len(bus.message_log()) >= 5


# ---------------------------------------------------------------------------
# AgentChannel typed helpers
# ---------------------------------------------------------------------------

class TestAgentChannel:

    def _bus_with(self, *ids):
        secret = os.urandom(16)
        idents = {i: AgentIdentity(i, secret) for i in ids}
        bus    = MessageBus(idents)
        return bus, idents

    def test_send_plan_creates_plan_message(self):
        bus, idents = self._bus_with("a", "b")
        ch = AgentChannel(idents["a"], bus)
        ch.send_plan("b", {"code": "x = 1"})
        msgs = bus.receive("b")
        assert msgs[0].msg_type == MsgType.PLAN
        assert msgs[0].payload["plan"]["code"] == "x = 1"

    def test_send_observation(self):
        bus, idents = self._bus_with("a", "b")
        ch = AgentChannel(idents["a"], bus)
        ch.send_observation("b", {"sensor": 42})
        msgs = bus.receive("b")
        assert msgs[0].msg_type == MsgType.OBSERVATION

    def test_send_critique(self):
        bus, idents = self._bus_with("a", "b")
        ch = AgentChannel(idents["a"], bus)
        ch.send_critique("b", "That plan looks risky", severity=7)
        msgs = bus.receive("b")
        assert msgs[0].msg_type == MsgType.CRITIQUE
        assert msgs[0].payload["severity"] == 7

    def test_bid(self):
        bus, idents = self._bus_with("a", "coordinator")
        ch = AgentChannel(idents["a"], bus)
        ch.bid("coordinator", "gpu_slot", 9.5)
        msgs = bus.receive("coordinator")
        assert msgs[0].msg_type == MsgType.BID
        assert msgs[0].payload["resource"] == "gpu_slot"
        assert msgs[0].payload["value"]    == pytest.approx(9.5)


# ---------------------------------------------------------------------------
# CoordinatorAgent tests
# ---------------------------------------------------------------------------

class TestCoordinatorAgent:

    def _make_coord_session(self, agent_ids, violation_threshold=3):
        secret   = SHARED_SECRET
        idents   = {aid: AgentIdentity(aid, secret) for aid in agent_ids}
        bus      = MessageBus(idents)
        channels = {aid: AgentChannel(ident, bus) for aid, ident in idents.items()}
        sup      = MCSSupervisor()
        coord    = CoordinatorAgent("coordinator", bus, sup, violation_threshold)
        return bus, channels, coord, sup

    def test_safe_plan_approved(self):
        bus, channels, coord, _ = self._make_coord_session(["a"])
        channels["a"].send_plan("coordinator", {"code": "x = 1 + 2"})
        result = coord.run_round()
        assert result.n_plans_approved == 1
        assert result.n_plans_rejected == 0
        assert result.safety_violations == []

    def test_unsafe_plan_rejected(self):
        bus, channels, coord, _ = self._make_coord_session(["a"])
        channels["a"].send_plan("coordinator", {"code": "import os\nos.system('rm -rf /')"})
        result = coord.run_round()
        assert result.n_plans_rejected >= 1
        assert len(result.safety_violations) >= 1

    def test_quarantine_after_threshold(self):
        threshold = 2
        bus, channels, coord, _ = self._make_coord_session(["rogue"], threshold)
        unsafe = {"code": "import subprocess\nsubprocess.run(['ls'])"}
        for _ in range(threshold):
            channels["rogue"].send_plan("coordinator", unsafe)
            coord.run_round()
        assert "rogue" in bus.quarantined_agents

    def test_benign_agent_not_quarantined_after_threshold_violations_by_rogue(self):
        bus, channels, coord, _ = self._make_coord_session(["rogue", "clean"], violation_threshold=2)
        unsafe = {"code": "import os"}
        safe   = {"code": "x = 42"}
        for _ in range(3):
            channels["rogue"].send_plan("coordinator", unsafe)
            channels["clean"].send_plan("coordinator", safe)
            coord.run_round()
        assert "rogue"  in  bus.quarantined_agents
        assert "clean"  not in bus.quarantined_agents

    def test_auction_awards_highest_bidder(self):
        bus, channels, coord, _ = self._make_coord_session(["a", "b"])
        channels["a"].bid("coordinator", "gpu", 3.0)
        channels["b"].bid("coordinator", "gpu", 9.9)
        result = coord.run_round()
        assert result.auction_awards.get("gpu") == "b"

    def test_auction_notifies_losers(self):
        bus, channels, coord, _ = self._make_coord_session(["a", "b"])
        channels["a"].bid("coordinator", "slot", 1.0)
        channels["b"].bid("coordinator", "slot", 5.0)
        coord.run_round()
        # Agent "a" should have received a REJECT (lost the auction)
        msgs_a = bus.receive("a")
        reject_msgs = [m for m in msgs_a if m.msg_type == MsgType.REJECT]
        assert len(reject_msgs) >= 1

    def test_violation_report_tracks_per_agent(self):
        bus, channels, coord, _ = self._make_coord_session(["rogue"], violation_threshold=10)
        unsafe = {"code": "import os"}
        for _ in range(3):
            channels["rogue"].send_plan("coordinator", unsafe)
            coord.run_round()
        report = coord.violation_report()
        assert report.get("rogue", 0) >= 3

    def test_empty_round_returns_zero_counts(self):
        bus, channels, coord, _ = self._make_coord_session(["a"])
        result = coord.run_round()
        assert result.n_plans_received == 0
        assert result.n_plans_approved == 0
        assert result.n_plans_rejected == 0

    def test_constitution_broadcast_sent(self):
        bus, channels, coord, _ = self._make_coord_session(["a", "b"])
        coord.broadcast_constitution()
        # Both agents should have received a BROADCAST constitution
        for aid in ["a", "b"]:
            msgs = bus.receive(aid)
            bc = [m for m in msgs if m.msg_type == MsgType.BROADCAST]
            assert any(m.payload.get("type") == "CONSTITUTION" for m in bc)


# ---------------------------------------------------------------------------
# MultiAgentSession tests
# ---------------------------------------------------------------------------

class TestMultiAgentSession:

    def test_make_session_creates_correct_agents(self, session_3):
        assert set(session_3.agent_ids) == {"alpha", "beta", "gamma"}

    def test_start_broadcasts_constitution(self, session_3):
        session_3.start()
        for aid in session_3.agent_ids:
            msgs = session_3.bus.receive(aid)
            assert any(m.payload.get("type") == "CONSTITUTION" for m in msgs)

    def test_finish_returns_session_summary(self, session_3):
        session_3.start()
        session_3.channels["alpha"].send_plan("coordinator", {"code": "x = 1"})
        session_3.coordinator.run_round()
        summary = session_3.finish()
        assert isinstance(summary, SessionSummary)
        assert summary.n_agents  == 3
        assert summary.n_rounds  == 1
        assert summary.wall_clock_s >= 0.0

    def test_full_round_trip(self):
        session = make_session(["a", "b", "c"], shared_secret=SHARED_SECRET)
        session.start()

        # Two safe plans, one bid
        session.channels["a"].send_plan("coordinator", {"code": "result = 2 ** 10"})
        session.channels["b"].send_plan("coordinator", {"code": "data = list(range(5))"})
        session.channels["c"].bid("coordinator", "cpu", 7.5)
        session.channels["a"].bid("coordinator", "cpu", 3.0)

        result  = session.coordinator.run_round()
        summary = session.finish()

        assert result.n_plans_approved >= 2
        assert result.auction_awards.get("cpu") == "c"  # highest bidder
        assert summary.total_violations == 0
        assert summary.quarantined == []

    def test_quarantine_reflected_in_summary(self):
        session = make_session(
            ["rogue", "clean"],
            shared_secret       = SHARED_SECRET,
            violation_threshold = 1,
        )
        session.start()
        unsafe = {"code": "import subprocess"}
        session.channels["rogue"].send_plan("coordinator", unsafe)
        session.coordinator.run_round()
        # Second violation to trigger quarantine (threshold=1 means 1 violation)
        session.channels["rogue"].send_plan("coordinator", unsafe)
        session.coordinator.run_round()

        summary = session.finish()
        assert "rogue" in summary.quarantined


# ---------------------------------------------------------------------------
# MultiAgentBenchmark tests
# ---------------------------------------------------------------------------

class TestMultiAgentBenchmark:

    @pytest.fixture(autouse=True)
    def bench(self):
        self.bench = MultiAgentBenchmark(n_rounds=3, n_resources=2, seed=0)

    def test_cooperative_safe_rate_is_one(self):
        result = self.bench.run("cooperative")
        assert result.scenario == "cooperative"
        # All benign plans — approval rate should be 1.0
        assert result.safe_rate == pytest.approx(1.0)
        assert result.n_violations == 0

    def test_adversarial_detects_violations(self):
        result = self.bench.run("adversarial")
        assert result.scenario == "adversarial"
        assert result.n_violations > 0
        assert result.n_plans_rejected > 0

    def test_adversarial_quarantines_rogue(self):
        result = self.bench.run("adversarial")
        assert result.n_quarantined >= 1

    def test_mixed_has_nonzero_auth_failures(self):
        result = self.bench.run("mixed")
        assert result.auth_failures > 0

    def test_run_all_returns_three_results(self):
        results = self.bench.run_all()
        assert len(results) == 3
        scenarios = {r.scenario for r in results}
        assert scenarios == {"cooperative", "adversarial", "mixed"}

    def test_result_has_round_results(self):
        result = self.bench.run("cooperative")
        assert len(result.round_results) == 3   # n_rounds=3

    def test_summary_table_is_non_empty_string(self):
        results = self.bench.run_all()
        table   = self.bench.summary_table(results)
        assert isinstance(table, str)
        assert "cooperative" in table
        assert "adversarial" in table
        assert "mixed" in table

    def test_unknown_scenario_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            self.bench.run("unknown_scenario")

    def test_result_summary_dict_has_required_keys(self):
        result = self.bench.run("cooperative")
        d      = result.summary_dict()
        for key in ["scenario", "n_agents", "n_rounds", "safe_rate",
                    "n_violations", "n_quarantined", "auction_gini",
                    "wall_clock_s"]:
            assert key in d, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Gini coefficient helper tests
# ---------------------------------------------------------------------------

class TestGiniHelper:

    def test_perfectly_equal_distribution(self):
        assert _gini([5, 5, 5, 5]) == pytest.approx(0.0)

    def test_perfectly_unequal_distribution(self):
        # All wins go to one agent
        g = _gini([0, 0, 0, 10])
        assert g > 0.5

    def test_empty_returns_zero(self):
        assert _gini([]) == pytest.approx(0.0)

    def test_all_zeros_returns_zero(self):
        assert _gini([0, 0, 0]) == pytest.approx(0.0)
