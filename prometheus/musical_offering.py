"""
Musical Offering - Multi-Agent Harmony (v0.95)

Inspired by Bach's "Musical Offering" from GEB, this implements harmonious
coordination between multiple agents, where each agent contributes its own
"voice" to create a coherent whole.

Key concepts:
- Canon: Multiple agents following the same strategy with time delays
- Fugue: Multiple agents with variations on a theme
- Counterpoint: Agents working in complementary ways
- Harmony: Agents coordinating to achieve shared goals
"""

from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import time


class VoiceType(Enum):
    """Types of voices in multi-agent coordination"""
    SUBJECT = "subject"  # Primary agent/strategy
    ANSWER = "answer"  # Response to subject (transposed)
    COUNTERSUBJECT = "countersubject"  # Complementary strategy
    AUGMENTATION = "augmentation"  # Same strategy, slower
    DIMINUTION = "diminution"  # Same strategy, faster
    INVERSION = "inversion"  # Opposite strategy


class CoordinationPattern(Enum):
    """Coordination patterns between agents"""
    CANON = "canon"  # Agents follow same strategy with time offset
    FUGUE = "fugue"  # Agents introduce theme in succession
    COUNTERPOINT = "counterpoint"  # Agents work in complementary ways
    UNISON = "unison"  # Agents act simultaneously
    HARMONY = "harmony"  # Agents create coherent whole


@dataclass
class AgentVoice:
    """
    A voice in the multi-agent ensemble

    Like a voice in a fugue, each agent has a role and timing
    """
    voice_id: str
    voice_type: VoiceType
    agent_name: str
    strategy: str
    entry_time: int  # When this voice enters (in time steps)
    tempo: float = 1.0  # Speed multiplier (1.0 = normal)
    active: bool = False
    performance_history: List[float] = field(default_factory=list)

    def get_avg_performance(self) -> float:
        """Get average performance of this voice"""
        if not self.performance_history:
            return 0.0
        return sum(self.performance_history) / len(self.performance_history)


@dataclass
class Ensemble:
    """
    A group of agents working together

    Like a musical ensemble, agents coordinate their actions
    """
    ensemble_id: str
    pattern: CoordinationPattern
    voices: List[AgentVoice] = field(default_factory=list)
    current_time: int = 0
    performance_log: List[Dict[str, Any]] = field(default_factory=list)

    def add_voice(self, voice: AgentVoice):
        """Add a voice to the ensemble"""
        self.voices.append(voice)

    def get_active_voices(self) -> List[AgentVoice]:
        """Get currently active voices"""
        return [v for v in self.voices if v.active]

    def step(self) -> List[AgentVoice]:
        """
        Advance one time step

        Returns:
            List of voices that should act this step
        """
        self.current_time += 1

        # Activate voices whose entry time has arrived
        for voice in self.voices:
            if not voice.active and voice.entry_time <= self.current_time:
                voice.active = True

        # Return active voices
        active = self.get_active_voices()

        # Log performance
        self.performance_log.append({
            'time': self.current_time,
            'active_voices': len(active),
            'voice_ids': [v.voice_id for v in active]
        })

        return active


class MusicalOffering:
    """
    Multi-agent coordination engine

    Orchestrates multiple agents to work in harmony like voices in a fugue
    """

    def __init__(self, offering_id: str = "musical_offering_001"):
        self.offering_id = offering_id
        self.ensembles = {}
        self.coordination_history = []

    def create_canon(self, subject_voice: AgentVoice, num_voices: int = 3,
                    time_offset: int = 2) -> Ensemble:
        """
        Create a canon - agents follow same strategy with time delays

        Args:
            subject_voice: The leading voice
            num_voices: Total number of voices
            time_offset: Time steps between voice entries

        Returns:
            Ensemble configured as a canon
        """
        ensemble = Ensemble(
            ensemble_id=f"CANON_{len(self.ensembles)}",
            pattern=CoordinationPattern.CANON
        )

        # Add subject voice
        ensemble.add_voice(subject_voice)

        # Add answer voices with time offsets
        for i in range(1, num_voices):
            answer = AgentVoice(
                voice_id=f"VOICE_{i}",
                voice_type=VoiceType.ANSWER,
                agent_name=f"agent_{i}",
                strategy=subject_voice.strategy,  # Same strategy
                entry_time=i * time_offset,
                tempo=subject_voice.tempo
            )
            ensemble.add_voice(answer)

        self.ensembles[ensemble.ensemble_id] = ensemble
        return ensemble

    def create_fugue(self, subject_strategy: str, num_voices: int = 4) -> Ensemble:
        """
        Create a fugue - agents introduce theme in succession with variations

        Args:
            subject_strategy: The main theme/strategy
            num_voices: Number of voices

        Returns:
            Ensemble configured as a fugue
        """
        ensemble = Ensemble(
            ensemble_id=f"FUGUE_{len(self.ensembles)}",
            pattern=CoordinationPattern.FUGUE
        )

        # Subject voice
        subject = AgentVoice(
            voice_id="SUBJECT",
            voice_type=VoiceType.SUBJECT,
            agent_name="subject_agent",
            strategy=subject_strategy,
            entry_time=0
        )
        ensemble.add_voice(subject)

        # Answer voice (enters after subject)
        answer = AgentVoice(
            voice_id="ANSWER",
            voice_type=VoiceType.ANSWER,
            agent_name="answer_agent",
            strategy=self._transpose_strategy(subject_strategy),
            entry_time=4
        )
        ensemble.add_voice(answer)

        # Countersubject (complementary strategy)
        countersubject = AgentVoice(
            voice_id="COUNTERSUBJECT",
            voice_type=VoiceType.COUNTERSUBJECT,
            agent_name="counter_agent",
            strategy=self._create_countersubject(subject_strategy),
            entry_time=8
        )
        ensemble.add_voice(countersubject)

        # Additional voices with variations
        if num_voices >= 4:
            augmentation = AgentVoice(
                voice_id="AUGMENTATION",
                voice_type=VoiceType.AUGMENTATION,
                agent_name="aug_agent",
                strategy=subject_strategy,
                entry_time=12,
                tempo=0.5  # Slower
            )
            ensemble.add_voice(augmentation)

        self.ensembles[ensemble.ensemble_id] = ensemble
        return ensemble

    def create_counterpoint(self, strategy_a: str, strategy_b: str) -> Ensemble:
        """
        Create counterpoint - two complementary strategies

        Args:
            strategy_a: First strategy
            strategy_b: Second complementary strategy

        Returns:
            Ensemble configured for counterpoint
        """
        ensemble = Ensemble(
            ensemble_id=f"COUNTERPOINT_{len(self.ensembles)}",
            pattern=CoordinationPattern.COUNTERPOINT
        )

        voice_a = AgentVoice(
            voice_id="VOICE_A",
            voice_type=VoiceType.SUBJECT,
            agent_name="agent_a",
            strategy=strategy_a,
            entry_time=0
        )

        voice_b = AgentVoice(
            voice_id="VOICE_B",
            voice_type=VoiceType.COUNTERSUBJECT,
            agent_name="agent_b",
            strategy=strategy_b,
            entry_time=0  # Start together
        )

        ensemble.add_voice(voice_a)
        ensemble.add_voice(voice_b)

        self.ensembles[ensemble.ensemble_id] = ensemble
        return ensemble

    def _transpose_strategy(self, strategy: str) -> str:
        """
        Transpose a strategy (like transposing music)

        Args:
            strategy: Original strategy

        Returns:
            Transposed strategy
        """
        # Simple transposition: maintain structure but change specifics
        # In music, transposition changes pitch but keeps intervals
        # Here, we keep strategic structure but vary tactics

        transposed = strategy.replace("center", "edge")
        transposed = transposed.replace("offensive", "defensive")

        if transposed == strategy:
            # If no changes, add variation
            transposed = strategy + " (varied)"

        return transposed

    def _create_countersubject(self, subject_strategy: str) -> str:
        """
        Create a countersubject - complementary strategy

        Args:
            subject_strategy: Main strategy

        Returns:
            Complementary strategy
        """
        # Countersubject should complement, not compete
        if "offensive" in subject_strategy.lower():
            return "Focus on defensive positioning and threat prevention"
        elif "defensive" in subject_strategy.lower():
            return "Focus on offensive opportunities and initiative"
        elif "center" in subject_strategy.lower():
            return "Focus on controlling edges and corners"
        else:
            return "Adapt to complement current strategy"

    def coordinate_ensemble(self, ensemble_id: str, num_steps: int = 10) -> List[Dict[str, Any]]:
        """
        Run ensemble coordination for multiple steps

        Args:
            ensemble_id: ID of ensemble to run
            num_steps: Number of time steps

        Returns:
            Coordination log
        """
        if ensemble_id not in self.ensembles:
            return []

        ensemble = self.ensembles[ensemble_id]
        coordination_log = []

        for step in range(num_steps):
            active_voices = ensemble.step()

            step_log = {
                'time': ensemble.current_time,
                'pattern': ensemble.pattern.value,
                'active_voices': len(active_voices),
                'voices': [
                    {
                        'id': v.voice_id,
                        'type': v.voice_type.value,
                        'strategy': v.strategy[:50] + "..." if len(v.strategy) > 50 else v.strategy,
                        'tempo': v.tempo
                    }
                    for v in active_voices
                ]
            }

            coordination_log.append(step_log)
            self.coordination_history.append(step_log)

        return coordination_log

    def measure_harmony(self, ensemble_id: str) -> float:
        """
        Measure harmoniousness of ensemble

        Args:
            ensemble_id: Ensemble to measure

        Returns:
            Harmony score (0.0 to 1.0)
        """
        if ensemble_id not in self.ensembles:
            return 0.0

        ensemble = self.ensembles[ensemble_id]
        active_voices = ensemble.get_active_voices()

        if not active_voices:
            return 0.0

        # Harmony based on:
        # 1. Performance of individual voices
        performances = [v.get_avg_performance() for v in active_voices]
        avg_performance = sum(performances) / len(performances) if performances else 0.0

        # 2. Coordination (are voices entering at right times?)
        proper_entries = sum(1 for v in ensemble.voices if v.active or v.entry_time > ensemble.current_time)
        entry_score = proper_entries / len(ensemble.voices)

        # 3. Diversity (variety in voice types)
        voice_types = set(v.voice_type for v in ensemble.voices)
        diversity_score = len(voice_types) / len(VoiceType)

        # Combine scores
        harmony = (avg_performance * 0.4 + entry_score * 0.3 + diversity_score * 0.3)

        return harmony

    def get_ensemble_stats(self, ensemble_id: str) -> Dict[str, Any]:
        """Get statistics for an ensemble"""
        if ensemble_id not in self.ensembles:
            return {}

        ensemble = self.ensembles[ensemble_id]

        return {
            'ensemble_id': ensemble_id,
            'pattern': ensemble.pattern.value,
            'total_voices': len(ensemble.voices),
            'active_voices': len(ensemble.get_active_voices()),
            'current_time': ensemble.current_time,
            'harmony': self.measure_harmony(ensemble_id),
            'voice_types': list(set(v.voice_type.value for v in ensemble.voices))
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics"""
        total_voices = sum(len(e.voices) for e in self.ensembles.values())
        total_active = sum(len(e.get_active_voices()) for e in self.ensembles.values())

        return {
            'offering_id': self.offering_id,
            'num_ensembles': len(self.ensembles),
            'total_voices': total_voices,
            'total_active_voices': total_active,
            'coordination_events': len(self.coordination_history),
            'patterns_used': list(set(e.pattern.value for e in self.ensembles.values()))
        }

    def visualize_ensemble(self, ensemble_id: str) -> str:
        """
        Create visualization of ensemble coordination

        Args:
            ensemble_id: Ensemble to visualize

        Returns:
            ASCII art visualization
        """
        if ensemble_id not in self.ensembles:
            return "Ensemble not found"

        ensemble = self.ensembles[ensemble_id]

        lines = [f"Ensemble: {ensemble_id} ({ensemble.pattern.value.upper()})"]
        lines.append("=" * 60)

        # Timeline visualization
        max_time = max((v.entry_time for v in ensemble.voices), default=0) + 10

        for voice in ensemble.voices:
            # Voice line
            voice_line = f"{voice.voice_id:15} "

            # Timeline
            timeline = ""
            for t in range(max_time):
                if t < voice.entry_time:
                    timeline += "·"
                elif t == voice.entry_time:
                    timeline += "▶"
                else:
                    timeline += "─"

            voice_line += timeline + f" [{voice.voice_type.value}]"
            lines.append(voice_line)

        lines.append("")
        lines.append(f"Current Time: {ensemble.current_time}")
        lines.append(f"Active Voices: {len(ensemble.get_active_voices())}")
        lines.append(f"Harmony: {self.measure_harmony(ensemble_id):.2f}")

        return "\n".join(lines)
