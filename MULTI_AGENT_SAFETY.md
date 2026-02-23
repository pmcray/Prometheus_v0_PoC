# Multi-Agent Safety Protocols — Prometheus v0.97 (WP5)

This document describes the threat model, design decisions, implemented
mitigations, and test coverage for the WP5 multi-agent communication and
coordination layer.

---

## Overview

WP5 adds a **secure inter-agent communication bus** and a
**safety-gated coordination layer** to Prometheus.  Multiple specialised
agents can now exchange signed messages, propose plans, bid for resources, and
receive coordination decisions — all gated through the existing
`MCSSupervisor` safety checks.

```
┌────────────┐   signed PLAN   ┌──────────────────────────────┐
│ AgentAlpha ├────────────────►│                              │
├────────────┤                 │     CoordinatorAgent         │
│  AgentBeta ├────────────────►│  verify_modification()       │
├────────────┤   signed BID    │  (MCSSupervisor)             │
│ AgentGamma ├────────────────►│  priority auction            │
└────────────┘                 └──────────────┬───────────────┘
                                              │ AWARD / REJECT / QUARANTINE
                              ┌───────────────▼───────────────┐
                              │          MessageBus           │
                              │  HMAC-SHA256 sign & verify    │
                              │  replay protection            │
                              │  quarantine enforcement       │
                              └───────────────────────────────┘
```

---

## Threat Model

| # | Attack surface | Threat actor | Attack class |
|---|----------------|-------------|--------------|
| 1 | `MessageBus.send()` | Any agent on the bus | **Message spoofing** — forge sender_id |
| 2 | `MessageBus.send()` | Any agent on the bus | **Replay attack** — re-send a captured message |
| 3 | `CoordinatorAgent.run_round()` | Agent submitting plans | **Code injection** — unsafe plan bypasses MCSSupervisor |
| 4 | `CoordinatorAgent.run_round()` | Agent submitting bids | **Auction manipulation** — collusion or shill bids |
| 5 | `MessageBus.receive()` | Man-in-the-middle | **Message tampering** — modify payload in transit |
| 6 | Overall system | Persistent violator | **Denial of service** — flood coordinator with unsafe plans |

---

## Design Decisions

### 1. Message Authentication — HMAC-SHA256

Every message carries an `AgentIdentity`-keyed HMAC-SHA256 signature over
the canonical serialisation of all immutable fields:

```
HMAC-SHA256(
  key   = agent_secret,
  data  = JSON({sender_id, recipient_id, msg_type, payload, seq_no, nonce, timestamp})
)
```

The `MessageBus` verifies each signature on `receive()` and silently drops
tampered messages.

**Why HMAC (symmetric) rather than RSA/ECDSA (asymmetric)?**

All agents run in the same Python process on the same host in this research
prototype.  A shared-secret MAC is sufficient and avoids the key-management
overhead of a full PKI.  Production deployment would require per-agent
asymmetric keys and a certificate authority.

### 2. Replay Protection

Each `AgentIdentity` maintains a monotonically increasing `_seq_counter`.
The `MessageBus` stores every seen `(sender_id, seq_no)` pair and rejects
duplicates immediately, before any payload inspection.

A 128-bit random `nonce` (UUID4 hex) is also included in the canonical bytes,
so even if an attacker could predict sequence numbers they would still need to
know the nonce to forge a valid MAC.

### 3. Safety Gating via MCSSupervisor

The `CoordinatorAgent` extracts the `code` field from every incoming `PLAN`
message and passes it to `MCSSupervisor.verify_modification()`.  Only plans
that return `critique.is_safe = True` are forwarded with an `AWARD`.

Unsafe plans produce a `REJECT` message with the violation type, description,
and severity from the `SafetyCritique`.

### 4. Quarantine

An agent that accumulates `violation_threshold` (default 3) safety violations
is **quarantined** by the bus.  Quarantined agents' `send()` calls return
`False` immediately — they cannot communicate further until explicitly
released.

A `QUARANTINE` broadcast is sent to all remaining agents to notify them.

### 5. Priority Auction (Resource Deconfliction)

When two or more agents bid for the same resource in the same round, the
`CoordinatorAgent` awards it to the **highest bidder** and sends `REJECT` to
all losers.  This is a simple Vickrey-adjacent first-price auction; a
second-price variant would provide truthful bidding incentives in a production
system.

Auction fairness is measured by the **Gini coefficient** over win counts
across agents: 0 = perfectly equal, 1 = monopoly.

---

## Implemented Mitigations

| Threat | Mitigation | Location |
|--------|-----------|----------|
| Message spoofing | HMAC-SHA256 per-message signature | `AgentIdentity.sign()` / `MessageBus._verify()` |
| Replay attack | `(sender_id, seq_no)` seen-set + random nonce | `MessageBus.send()` |
| Code injection via plan | MCSSupervisor gate in every round | `CoordinatorAgent.run_round()` |
| Message tampering | Signature verification on `receive()` | `MessageBus.receive()` |
| DoS via repeated violations | Quarantine after threshold | `CoordinatorAgent.run_round()` |
| Unknown sender | `_identities` lookup — unknown sender fails verify | `MessageBus._verify()` |
| Resource monopoly | Priority auction + Gini monitoring | `CoordinatorAgent.run_round()` |

---

## Test Coverage

All tests are in `tests/test_multi_agent.py` (52 tests, all passing):

| Class | Tests | What is tested |
|-------|-------|----------------|
| `TestAgentIdentity` | 6 | HMAC sign/verify, seq monotonicity, random secret |
| `TestMessage` | 4 | Canonical bytes determinism, payload change detection, serialisation round-trip, nonce uniqueness |
| `TestMessageBus` | 11 | Delivery, inbox clear, peek, unknown recipient, replay rejection, quarantine block/release, broadcast, tampering drop, stats, log growth |
| `TestAgentChannel` | 4 | Typed helpers: plan, observation, critique, bid |
| `TestCoordinatorAgent` | 9 | Safe plan approved, unsafe plan rejected, quarantine after threshold, benign unaffected, auction winner, auction loser notified, violation report, empty round, constitution broadcast |
| `TestMultiAgentSession` | 5 | Agent creation, start/constitution, finish/summary, full round-trip, quarantine in summary |
| `TestMultiAgentBenchmark` | 9 | Cooperative safe_rate=1, adversarial violations detected, rogue quarantined, mixed auth failures, run_all three results, round_results present, summary table, unknown scenario error, summary dict keys |
| `TestGiniHelper` | 4 | Equal distribution, unequal, empty, all-zeros |

Run all:
```bash
pytest tests/test_multi_agent.py -v
```

---

## Benchmark Results (reference run)

```
Scenario       Agents Rounds   Msgs  Safe%  Viols  Quar   Gini  AuthF  Time(s)
-------------------------------------------------------------------------------
cooperative         4      5    ...  100.0      0     0    ...      0   <0.01
adversarial         4      5    ...   <100     >0     1    ...      0   <0.01
mixed               5      5    ...   <100     >0   0-1    ...     >0   <0.01
```

- **cooperative**: All benign agents; safe_rate = 1.0, zero violations.
- **adversarial**: Rogue agent quarantined after `violation_threshold`
  violations; benign agents unaffected.
- **mixed**: Combination of safe/unsafe plans and simulated unregistered-agent
  messages (auth failures counted).

Run the benchmark:
```bash
python benchmarks/multi_agent_benchmark.py
```

---

## Residual Risks

| Risk | Likelihood | Mitigation gap |
|------|-----------|----------------|
| **Shared-secret compromise** — all agents use the same HMAC key | LOW (single host) | Requires PKI for multi-host deployment |
| **Shill bidding** — colluding agents coordinate bids out-of-band | LOW | No cross-agent communication audit in current auction |
| **Semantic code injection** — plan code passes AST checks but encodes harm in logic | MEDIUM | Requires semantic / LLM-based plan review (not yet implemented) |
| **Coordinator single point of failure** — if coordinator is compromised all safety gating is bypassed | LOW | Requires multi-coordinator consensus for production |
| **Quarantine bypass** — quarantined agent creates new identity and re-registers | LOW | Registration requires coordinator approval in production |

---

## Recommended Next Steps

1. Replace shared-secret HMAC with per-agent asymmetric keys (ECDSA P-256)
   and a lightweight PKI for multi-host deployment.
2. Extend `CoordinatorAgent` to support **multi-coordinator quorum** so no
   single coordinator is a single point of failure.
3. Add a **second-price (Vickrey) auction** for truthful bidding incentives.
4. Integrate `CodeInjectionGuard` (WP3) into the plan-safety gate as an
   additional layer alongside `MCSSupervisor`.
5. Add a **rate limiter** to the bus to defend against message-flood DoS.

---

*Generated by WP5 Multi-Agent Safety analysis — Prometheus v0.97*
