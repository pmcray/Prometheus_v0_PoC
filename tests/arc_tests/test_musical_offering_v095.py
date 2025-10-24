#!/usr/bin/env python3
"""
Test Musical Offering (v0.95) - Multi-Agent Harmony

Tests harmonious coordination between multiple agents inspired by
Bach's Musical Offering and GEB concepts.
"""

import sys
from prometheus.musical_offering import (
    MusicalOffering, AgentVoice, Ensemble,
    VoiceType, CoordinationPattern
)


def test_agent_voice():
    """Test creating agent voices"""
    print("🧪 Testing Agent Voice...")
    print("-" * 60)

    voice = AgentVoice(
        voice_id="VOICE_001",
        voice_type=VoiceType.SUBJECT,
        agent_name="test_agent",
        strategy="Prioritize center control",
        entry_time=0,
        tempo=1.0
    )

    assert voice.voice_id == "VOICE_001"
    assert voice.voice_type == VoiceType.SUBJECT
    assert not voice.active
    print(f"  ✓ Created voice: {voice.voice_id} ({voice.voice_type.value})")

    # Test performance tracking
    voice.performance_history = [0.8, 0.9, 0.85]
    avg = voice.get_avg_performance()
    assert abs(avg - 0.85) < 0.01
    print(f"  ✓ Average performance: {avg:.2f}")

    print("  ✓ Agent Voice: PASSED\n")


def test_ensemble():
    """Test ensemble creation and management"""
    print("🧪 Testing Ensemble...")
    print("-" * 60)

    ensemble = Ensemble(
        ensemble_id="TEST_ENSEMBLE",
        pattern=CoordinationPattern.CANON
    )

    # Add voices
    voice1 = AgentVoice("V1", VoiceType.SUBJECT, "agent1", "Strategy A", entry_time=0)
    voice2 = AgentVoice("V2", VoiceType.ANSWER, "agent2", "Strategy A", entry_time=2)

    ensemble.add_voice(voice1)
    ensemble.add_voice(voice2)

    assert len(ensemble.voices) == 2
    print(f"  ✓ Created ensemble with {len(ensemble.voices)} voices")

    # Test stepping
    active = ensemble.step()  # Time 1
    assert len(active) == 1  # Only voice1 active (entry_time=0)
    print(f"  ✓ Time 1: {len(active)} voice active")

    active = ensemble.step()  # Time 2
    assert len(active) == 2  # Both voices active (voice2 entry_time=2)
    print(f"  ✓ Time 2: {len(active)} voices active")

    active = ensemble.step()  # Time 3
    assert len(active) == 2  # Both voices still active
    print(f"  ✓ Time 3: {len(active)} voices active")

    print("  ✓ Ensemble: PASSED\n")


def test_canon_creation():
    """Test creating a canon"""
    print("🧪 Testing Canon Creation...")
    print("-" * 60)

    offering = MusicalOffering("test_offering")

    subject = AgentVoice(
        voice_id="SUBJECT",
        voice_type=VoiceType.SUBJECT,
        agent_name="subject_agent",
        strategy="Prioritize center control and blocking",
        entry_time=0
    )

    canon = offering.create_canon(subject, num_voices=3, time_offset=2)

    assert canon is not None
    assert len(canon.voices) == 3
    assert canon.pattern == CoordinationPattern.CANON
    print(f"  ✓ Created canon with {len(canon.voices)} voices")

    # Check voice entry times
    entry_times = [v.entry_time for v in canon.voices]
    assert entry_times == [0, 2, 4]
    print(f"  ✓ Entry times: {entry_times}")

    # Check all voices have same strategy (it's a canon)
    strategies = [v.strategy for v in canon.voices]
    assert all(s == subject.strategy for s in strategies)
    print(f"  ✓ All voices use same strategy (canon property)")

    print("  ✓ Canon Creation: PASSED\n")


def test_fugue_creation():
    """Test creating a fugue"""
    print("🧪 Testing Fugue Creation...")
    print("-" * 60)

    offering = MusicalOffering("fugue_test")

    subject_strategy = "Focus on offensive center control"

    fugue = offering.create_fugue(subject_strategy, num_voices=4)

    assert fugue is not None
    assert len(fugue.voices) == 4
    assert fugue.pattern == CoordinationPattern.FUGUE
    print(f"  ✓ Created fugue with {len(fugue.voices)} voices")

    # Check voice types
    voice_types = [v.voice_type for v in fugue.voices]
    assert VoiceType.SUBJECT in voice_types
    assert VoiceType.ANSWER in voice_types
    assert VoiceType.COUNTERSUBJECT in voice_types
    print(f"  ✓ Voice types present: {len(set(voice_types))} unique types")

    # Check entries are staggered
    entry_times = [v.entry_time for v in fugue.voices]
    assert sorted(entry_times) == entry_times  # Should be in order
    print(f"  ✓ Staggered entry times: {entry_times}")

    # Check augmentation has slower tempo
    aug_voice = next((v for v in fugue.voices if v.voice_type == VoiceType.AUGMENTATION), None)
    if aug_voice:
        assert aug_voice.tempo < 1.0
        print(f"  ✓ Augmentation voice has tempo: {aug_voice.tempo}")

    print("  ✓ Fugue Creation: PASSED\n")


def test_counterpoint_creation():
    """Test creating counterpoint"""
    print("🧪 Testing Counterpoint Creation...")
    print("-" * 60)

    offering = MusicalOffering("counterpoint_test")

    strategy_a = "Focus on offensive positioning"
    strategy_b = "Focus on defensive positioning"

    counterpoint = offering.create_counterpoint(strategy_a, strategy_b)

    assert counterpoint is not None
    assert len(counterpoint.voices) == 2
    assert counterpoint.pattern == CoordinationPattern.COUNTERPOINT
    print(f"  ✓ Created counterpoint with {len(counterpoint.voices)} voices")

    # Both voices should start together (entry_time = 0)
    entry_times = [v.entry_time for v in counterpoint.voices]
    assert all(t == 0 for t in entry_times)
    print(f"  ✓ Both voices enter simultaneously")

    # Strategies should be different (complementary)
    strategies = [v.strategy for v in counterpoint.voices]
    assert strategies[0] != strategies[1]
    print(f"  ✓ Strategies are complementary")

    print("  ✓ Counterpoint Creation: PASSED\n")


def test_ensemble_coordination():
    """Test coordinating an ensemble"""
    print("🧪 Testing Ensemble Coordination...")
    print("-" * 60)

    offering = MusicalOffering("coordination_test")

    subject = AgentVoice("SUBJ", VoiceType.SUBJECT, "agent", "Test strategy", entry_time=0)
    canon = offering.create_canon(subject, num_voices=3, time_offset=2)

    # Run coordination
    log = offering.coordinate_ensemble(canon.ensemble_id, num_steps=10)

    assert len(log) == 10
    print(f"  ✓ Coordination ran for {len(log)} steps")

    # Check voices become active over time
    active_counts = [step['active_voices'] for step in log]
    assert active_counts[0] == 1  # First step: 1 voice
    assert active_counts[2] >= 2  # Third step: 2+ voices
    assert active_counts[-1] == 3  # Final step: all 3 voices
    print(f"  ✓ Active voice progression: {active_counts[0]} → {active_counts[2]} → {active_counts[-1]}")

    print("  ✓ Ensemble Coordination: PASSED\n")


def test_harmony_measurement():
    """Test measuring harmony"""
    print("🧪 Testing Harmony Measurement...")
    print("-" * 60)

    offering = MusicalOffering("harmony_test")

    subject = AgentVoice("SUBJ", VoiceType.SUBJECT, "agent", "Test", entry_time=0)
    canon = offering.create_canon(subject, num_voices=3, time_offset=2)

    # Initial harmony (no voices active yet)
    harmony_initial = offering.measure_harmony(canon.ensemble_id)
    print(f"  ✓ Initial harmony: {harmony_initial:.2f}")

    # Step forward to activate voices
    offering.coordinate_ensemble(canon.ensemble_id, num_steps=5)

    # Measure harmony with active voices
    harmony_active = offering.measure_harmony(canon.ensemble_id)
    print(f"  ✓ Harmony with active voices: {harmony_active:.2f}")

    # Add performance history
    for voice in canon.voices:
        voice.performance_history = [0.8, 0.9, 0.85]

    # Measure harmony with performance data
    harmony_performing = offering.measure_harmony(canon.ensemble_id)
    assert harmony_performing > harmony_active
    print(f"  ✓ Harmony with performance: {harmony_performing:.2f}")

    print("  ✓ Harmony Measurement: PASSED\n")


def test_strategy_transposition():
    """Test strategy transposition"""
    print("🧪 Testing Strategy Transposition...")
    print("-" * 60)

    offering = MusicalOffering("transpose_test")

    # Test transposition
    original = "Focus on center control and offensive play"
    transposed = offering._transpose_strategy(original)

    assert transposed != original
    print(f"  ✓ Original: {original}")
    print(f"  ✓ Transposed: {transposed}")

    # Check that structure is maintained (like musical transposition)
    assert len(transposed) > 0
    print(f"  ✓ Transposition maintains structure")

    print("  ✓ Strategy Transposition: PASSED\n")


def test_countersubject_creation():
    """Test countersubject creation"""
    print("🧪 Testing Countersubject Creation...")
    print("-" * 60)

    offering = MusicalOffering("counter_test")

    # Test offensive → defensive
    offensive = "Focus on offensive positioning"
    counter1 = offering._create_countersubject(offensive)
    assert "defensive" in counter1.lower()
    print(f"  ✓ Offensive strategy → {counter1[:50]}...")

    # Test defensive → offensive
    defensive = "Focus on defensive positioning"
    counter2 = offering._create_countersubject(defensive)
    assert "offensive" in counter2.lower()
    print(f"  ✓ Defensive strategy → {counter2[:50]}...")

    # Test center → edges
    center = "Control the center positions"
    counter3 = offering._create_countersubject(center)
    assert "edge" in counter3.lower() or "corner" in counter3.lower()
    print(f"  ✓ Center strategy → {counter3[:50]}...")

    print("  ✓ Countersubject Creation: PASSED\n")


def test_ensemble_stats():
    """Test getting ensemble statistics"""
    print("🧪 Testing Ensemble Statistics...")
    print("-" * 60)

    offering = MusicalOffering("stats_test")

    subject = AgentVoice("SUBJ", VoiceType.SUBJECT, "agent", "Test", entry_time=0)
    fugue = offering.create_fugue("Test strategy", num_voices=4)

    # Run some coordination
    offering.coordinate_ensemble(fugue.ensemble_id, num_steps=15)

    # Get stats
    stats = offering.get_ensemble_stats(fugue.ensemble_id)

    assert stats['pattern'] == 'fugue'
    assert stats['total_voices'] == 4
    assert stats['active_voices'] > 0
    print(f"  ✓ Ensemble statistics:")
    for key, value in stats.items():
        print(f"    - {key}: {value}")

    print("  ✓ Ensemble Statistics: PASSED\n")


def test_overall_stats():
    """Test getting overall statistics"""
    print("🧪 Testing Overall Statistics...")
    print("-" * 60)

    offering = MusicalOffering("overall_test")

    # Create multiple ensembles
    subject1 = AgentVoice("S1", VoiceType.SUBJECT, "a1", "Strategy 1", entry_time=0)
    offering.create_canon(subject1, num_voices=3)

    offering.create_fugue("Strategy 2", num_voices=4)

    offering.create_counterpoint("Strategy A", "Strategy B")

    # Get stats
    stats = offering.get_stats()

    assert stats['num_ensembles'] == 3
    assert stats['total_voices'] > 0
    assert len(stats['patterns_used']) > 0
    print(f"  ✓ Overall statistics:")
    for key, value in stats.items():
        print(f"    - {key}: {value}")

    print("  ✓ Overall Statistics: PASSED\n")


def test_visualization():
    """Test ensemble visualization"""
    print("🧪 Testing Ensemble Visualization...")
    print("-" * 60)

    offering = MusicalOffering("viz_test")

    subject = AgentVoice("SUBJECT", VoiceType.SUBJECT, "agent", "Test strategy", entry_time=0)
    canon = offering.create_canon(subject, num_voices=3, time_offset=3)

    # Advance time
    offering.coordinate_ensemble(canon.ensemble_id, num_steps=8)

    # Get visualization
    viz = offering.visualize_ensemble(canon.ensemble_id)

    assert "CANON" in viz
    assert "Harmony" in viz
    assert "▶" in viz  # Entry marker
    print(f"  ✓ Generated visualization ({len(viz)} chars)")
    print("\n" + "=" * 60)
    print(viz)
    print("=" * 60 + "\n")

    print("  ✓ Ensemble Visualization: PASSED\n")


def main():
    print("=" * 60)
    print("  PROMETHEUS v0.95 MUSICAL OFFERING TEST SUITE")
    print("=" * 60)
    print()

    try:
        # Run all tests
        test_agent_voice()
        test_ensemble()
        test_canon_creation()
        test_fugue_creation()
        test_counterpoint_creation()
        test_ensemble_coordination()
        test_harmony_measurement()
        test_strategy_transposition()
        test_countersubject_creation()
        test_ensemble_stats()
        test_overall_stats()
        test_visualization()

        print("=" * 60)
        print("  ✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("v0.95 Musical Offering Features Verified:")
        print("  ✓ Agent voice creation and management")
        print("  ✓ Ensemble coordination patterns")
        print("  ✓ Canon (same strategy, time offset)")
        print("  ✓ Fugue (theme with variations)")
        print("  ✓ Counterpoint (complementary strategies)")
        print("  ✓ Harmony measurement")
        print("  ✓ Strategy transposition")
        print("  ✓ Countersubject generation")
        print("  ✓ Timeline visualization")
        print()
        print("System Status: OPERATIONAL")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
