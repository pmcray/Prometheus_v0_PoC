"""
Personalized Improvement Pathways v0.1 (v0.62)
Individualized learning paths and improvement strategies

Implements comprehensive personalization for agent improvement:
- Individual learning style adaptation
- Personalized curriculum sequencing
- Adaptive feedback and guidance systems
- Learning preference modeling
- Performance-based pathway optimization
"""

import random
import statistics
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json

from .adaptive_challenges import Challenge, ChallengeAttempt, AgentProfile, ChallengeCategory, DifficultyLevel
from .difficulty_scaling import ProgressionPlan, SkillMetrics, ProgressionState

class LearningStyle(Enum):
    """Different learning style preferences"""
    VISUAL = "visual"                   # Learns best with visual aids and examples
    KINESTHETIC = "kinesthetic"         # Learns best through hands-on practice
    ANALYTICAL = "analytical"           # Learns best through logical analysis
    INTUITIVE = "intuitive"             # Learns best through patterns and insights
    SEQUENTIAL = "sequential"           # Learns best with step-by-step progression
    GLOBAL = "global"                   # Learns best with big-picture understanding

class FeedbackStyle(Enum):
    """Different feedback delivery styles"""
    DETAILED = "detailed"               # Comprehensive explanations
    CONCISE = "concise"                 # Brief, to-the-point feedback
    ENCOURAGING = "encouraging"         # Positive, motivating feedback
    DIRECT = "direct"                   # Straightforward, honest feedback
    SOCRATIC = "socratic"               # Question-based guidance
    EXAMPLE_BASED = "example_based"     # Learning through examples

@dataclass
class LearningPreferences:
    """Comprehensive learning preferences for an agent"""
    agent_id: str
    primary_learning_style: LearningStyle
    secondary_learning_style: Optional[LearningStyle]
    preferred_feedback_style: FeedbackStyle
    optimal_session_length: int        # Minutes
    preferred_difficulty_progression: str  # "gradual", "steep", "mixed"
    challenge_variety_preference: float    # 0.0 (routine) to 1.0 (variety)
    collaboration_preference: float       # 0.0 (solo) to 1.0 (collaborative)
    error_tolerance: float                # 0.0 (low) to 1.0 (high)
    persistence_level: float              # 0.0 (gives up easily) to 1.0 (highly persistent)
    curiosity_drive: float                # 0.0 (focused) to 1.0 (exploratory)
    last_updated: str

@dataclass
class PersonalizedMilestone:
    """A personalized milestone in an agent's learning journey"""
    milestone_id: str
    agent_id: str
    skill_focus: str
    title: str
    description: str
    target_proficiency: float
    estimated_completion: str
    prerequisite_milestones: List[str]
    success_criteria: Dict[str, Any]
    rewards: List[str]
    personalized_guidance: str
    adaptive_content: Dict[str, Any]

@dataclass
class LearningPathway:
    """Complete personalized learning pathway for an agent"""
    pathway_id: str
    agent_id: str
    pathway_name: str
    overall_objective: str
    milestones: List[PersonalizedMilestone]
    estimated_duration_days: int
    current_position: int               # Current milestone index
    completion_percentage: float
    adaptive_adjustments: List[str]
    personalization_factors: Dict[str, Any]
    creation_date: str

@dataclass
class PersonalizedChallenge:
    """A challenge specifically tailored to an individual agent"""
    base_challenge: Challenge
    personalized_elements: Dict[str, Any]
    learning_style_adaptations: List[str]
    feedback_customizations: Dict[str, Any]
    difficulty_adjustments: Dict[str, float]
    motivational_elements: List[str]

class LearningStyleAnalyzer:
    """Analyzes and identifies agent learning styles"""

    def __init__(self):
        self.style_indicators = {
            LearningStyle.VISUAL: {
                "preferences": ["examples", "diagrams", "visualization"],
                "behaviors": ["requests_examples", "benefits_from_visual_aids"],
                "performance_patterns": ["better_with_visual_problems"]
            },
            LearningStyle.KINESTHETIC: {
                "preferences": ["hands_on", "practice", "experimentation"],
                "behaviors": ["tries_multiple_approaches", "learns_by_doing"],
                "performance_patterns": ["improves_with_practice_intensive_challenges"]
            },
            LearningStyle.ANALYTICAL: {
                "preferences": ["step_by_step", "logical_reasoning", "detailed_explanations"],
                "behaviors": ["systematic_approach", "seeks_understanding"],
                "performance_patterns": ["excels_at_algorithmic_challenges"]
            },
            LearningStyle.INTUITIVE: {
                "preferences": ["patterns", "big_picture", "creative_solutions"],
                "behaviors": ["jumps_to_insights", "sees_patterns_quickly"],
                "performance_patterns": ["good_at_design_challenges"]
            },
            LearningStyle.SEQUENTIAL: {
                "preferences": ["ordered_progression", "building_blocks", "structured_learning"],
                "behaviors": ["follows_curriculum_order", "completes_prerequisites"],
                "performance_patterns": ["steady_gradual_improvement"]
            },
            LearningStyle.GLOBAL: {
                "preferences": ["context", "connections", "overview_first"],
                "behaviors": ["seeks_broader_context", "connects_concepts"],
                "performance_patterns": ["performs_better_with_context"]
            }
        }

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def analyze_learning_style(self, agent_profile: AgentProfile,
                              challenge_attempts: List[ChallengeAttempt]) -> LearningPreferences:
        """Analyze agent's learning style from behavior and performance patterns"""

        self.logger.info(f"🧠 Analyzing learning style for agent {agent_profile.agent_id}")

        # Score each learning style based on evidence
        style_scores = {style: 0.0 for style in LearningStyle}

        # Analyze performance patterns
        for style, indicators in self.style_indicators.items():
            score = self._calculate_style_score(style, agent_profile, challenge_attempts, indicators)
            style_scores[style] = score

        # Determine primary and secondary learning styles
        sorted_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
        primary_style = sorted_styles[0][0]
        secondary_style = sorted_styles[1][0] if sorted_styles[1][1] > 0.3 else None

        # Determine feedback style preferences
        feedback_style = self._determine_feedback_style(agent_profile, challenge_attempts)

        # Calculate other preferences
        preferences = LearningPreferences(
            agent_id=agent_profile.agent_id,
            primary_learning_style=primary_style,
            secondary_learning_style=secondary_style,
            preferred_feedback_style=feedback_style,
            optimal_session_length=self._estimate_optimal_session_length(challenge_attempts),
            preferred_difficulty_progression=self._analyze_difficulty_progression_preference(challenge_attempts),
            challenge_variety_preference=self._calculate_variety_preference(agent_profile),
            collaboration_preference=self._assess_collaboration_preference(agent_profile),
            error_tolerance=self._calculate_error_tolerance(challenge_attempts),
            persistence_level=self._assess_persistence_level(challenge_attempts),
            curiosity_drive=self._assess_curiosity_drive(agent_profile),
            last_updated=datetime.now().isoformat()
        )

        self.logger.info(f"✅ Identified learning style: {primary_style.value} "
                        f"(secondary: {secondary_style.value if secondary_style else 'none'})")

        return preferences

    def _calculate_style_score(self, style: LearningStyle, agent_profile: AgentProfile,
                              attempts: List[ChallengeAttempt], indicators: Dict[str, List[str]]) -> float:
        """Calculate score for a specific learning style"""
        score = 0.0

        # Check performance patterns
        performance_patterns = indicators.get("performance_patterns", [])
        for pattern in performance_patterns:
            if pattern == "better_with_visual_problems":
                # Check performance on challenges that benefit from visualization
                visual_challenges = [a for a in attempts if "visual" in a.challenge_id.lower()]
                if visual_challenges:
                    avg_score = np.mean([a.score for a in visual_challenges if a.score is not None])
                    score += min(0.3, avg_score - 0.5)  # Bonus if above average

            elif pattern == "improves_with_practice_intensive_challenges":
                # Check improvement rate over time
                if len(attempts) > 5:
                    recent_scores = [a.score for a in attempts[-5:] if a.score is not None]
                    early_scores = [a.score for a in attempts[:5] if a.score is not None]
                    if recent_scores and early_scores:
                        improvement = np.mean(recent_scores) - np.mean(early_scores)
                        score += min(0.3, improvement)

            elif pattern == "excels_at_algorithmic_challenges":
                # Check performance on algorithmic challenges
                algo_attempts = [a for a in attempts if "algorithm" in a.challenge_id.lower()]
                if algo_attempts:
                    avg_score = np.mean([a.score for a in algo_attempts if a.score is not None])
                    if avg_score > 0.7:
                        score += 0.4

        # Check behavioral indicators (simplified - would need more data in practice)
        behaviors = indicators.get("behaviors", [])
        for behavior in behaviors:
            if behavior == "systematic_approach":
                # Infer from low error rates and consistent performance
                error_counts = [len(a.errors_encountered) for a in attempts]
                if error_counts and np.mean(error_counts) < 2:
                    score += 0.2

        return min(1.0, max(0.0, score))

    def _determine_feedback_style(self, agent_profile: AgentProfile,
                                 attempts: List[ChallengeAttempt]) -> FeedbackStyle:
        """Determine preferred feedback style"""

        # Analyze response to different types of challenges and feedback
        # This is simplified - in practice would track response to different feedback types

        # Check current focus areas for hints about feedback preferences
        if any("detail" in area.lower() for area in agent_profile.current_focus_areas):
            return FeedbackStyle.DETAILED
        elif any("example" in area.lower() for area in agent_profile.current_focus_areas):
            return FeedbackStyle.EXAMPLE_BASED
        elif len(attempts) > 20:  # Experienced agents might prefer concise feedback
            return FeedbackStyle.CONCISE
        else:
            return FeedbackStyle.ENCOURAGING  # Default for new learners

    def _estimate_optimal_session_length(self, attempts: List[ChallengeAttempt]) -> int:
        """Estimate optimal learning session length"""
        if not attempts:
            return 45  # Default

        # Analyze attempt patterns (simplified)
        # In practice, would track session lengths and performance correlation

        avg_attempt_time = np.mean([30 for _ in attempts])  # Placeholder - would use actual time data

        # Estimate based on persistence and complexity preferences
        return min(90, max(15, int(avg_attempt_time * 2)))

    def _analyze_difficulty_progression_preference(self, attempts: List[ChallengeAttempt]) -> str:
        """Analyze preferred difficulty progression style"""
        if len(attempts) < 5:
            return "gradual"

        # Analyze how agent performs with difficulty jumps vs gradual increases
        # Simplified analysis
        success_rates = [1.0 if a.success else 0.0 for a in attempts]

        if len(success_rates) > 5:
            # Check stability of performance
            recent_variance = np.var(success_rates[-10:]) if len(success_rates) >= 10 else np.var(success_rates)

            if recent_variance < 0.1:
                return "steep"  # Can handle difficulty jumps
            elif recent_variance > 0.3:
                return "mixed"  # Inconsistent, needs variety
            else:
                return "gradual"  # Steady progression works best

        return "gradual"

    def _calculate_variety_preference(self, agent_profile: AgentProfile) -> float:
        """Calculate preference for challenge variety"""
        # Check diversity of focus areas and success across categories
        focus_diversity = len(set(agent_profile.current_focus_areas))
        category_diversity = len(agent_profile.success_rates)

        # Normalize to 0-1 range
        variety_score = min(1.0, (focus_diversity + category_diversity) / 10.0)
        return variety_score

    def _assess_collaboration_preference(self, agent_profile: AgentProfile) -> float:
        """Assess preference for collaborative vs solo learning"""
        # Check for collaboration-related focus areas or preferences
        collab_indicators = ["collaboration", "team", "pair", "group"]

        collab_score = sum(0.2 for area in agent_profile.current_focus_areas
                          if any(indicator in area.lower() for indicator in collab_indicators))

        return min(1.0, collab_score)

    def _calculate_error_tolerance(self, attempts: List[ChallengeAttempt]) -> float:
        """Calculate tolerance for errors and failures"""
        if not attempts:
            return 0.5

        # Look at persistence despite failures
        consecutive_failures = 0
        max_consecutive_failures = 0

        for attempt in attempts:
            if not attempt.success:
                consecutive_failures += 1
                max_consecutive_failures = max(max_consecutive_failures, consecutive_failures)
            else:
                consecutive_failures = 0

        # Higher tolerance if agent continues despite multiple failures
        error_tolerance = min(1.0, max_consecutive_failures / 10.0)
        return error_tolerance

    def _assess_persistence_level(self, attempts: List[ChallengeAttempt]) -> float:
        """Assess agent's persistence level"""
        if len(attempts) < 3:
            return 0.5

        # Look for patterns of continued effort despite difficulties
        total_attempts = len(attempts)
        failed_attempts = len([a for a in attempts if not a.success])

        if failed_attempts == 0:
            return 0.7  # Good performance, moderate persistence needed

        # Higher persistence if agent keeps trying despite failures
        persistence = min(1.0, total_attempts / max(1, failed_attempts * 2))
        return persistence

    def _assess_curiosity_drive(self, agent_profile: AgentProfile) -> float:
        """Assess level of curiosity and exploration drive"""
        # Check diversity of interests and exploration patterns
        exploration_indicators = len(agent_profile.current_focus_areas) / 10.0
        category_breadth = len(agent_profile.success_rates) / len(ChallengeCategory)

        curiosity_score = (exploration_indicators + category_breadth) / 2.0
        return min(1.0, curiosity_score)

class PersonalizedPathwayGenerator:
    """Generates personalized learning pathways"""

    def __init__(self):
        self.learning_analyzer = LearningStyleAnalyzer()

        # Skill dependency mapping
        self.skill_dependencies = {
            "basic_syntax": [],
            "control_flow": ["basic_syntax"],
            "functions": ["basic_syntax", "control_flow"],
            "data_structures": ["basic_syntax", "functions"],
            "algorithms": ["functions", "data_structures", "control_flow"],
            "optimization": ["algorithms", "data_structures"],
            "design_patterns": ["functions", "data_structures"],
            "debugging": ["basic_syntax", "control_flow"],
            "testing": ["functions"],
            "refactoring": ["functions", "design_patterns"],
            "performance": ["algorithms", "optimization"],
            "security": ["basic_syntax", "functions"],
            "architecture": ["design_patterns", "functions"]
        }

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def generate_personalized_pathway(self, agent_profile: AgentProfile,
                                    learning_preferences: LearningPreferences,
                                    target_skills: List[str],
                                    time_constraint_days: Optional[int] = None) -> LearningPathway:
        """Generate a complete personalized learning pathway"""

        self.logger.info(f"🛤️ Generating personalized pathway for agent {agent_profile.agent_id}")

        # Create personalized milestones
        milestones = self._create_personalized_milestones(
            agent_profile, learning_preferences, target_skills
        )

        # Sequence milestones based on dependencies and preferences
        sequenced_milestones = self._sequence_milestones(milestones, learning_preferences)

        # Estimate duration
        estimated_duration = self._estimate_pathway_duration(
            sequenced_milestones, learning_preferences, time_constraint_days
        )

        # Create pathway
        pathway = LearningPathway(
            pathway_id=f"pathway_{agent_profile.agent_id}_{datetime.now().strftime('%Y%m%d')}",
            agent_id=agent_profile.agent_id,
            pathway_name=f"Personalized Learning Path for {agent_profile.agent_id}",
            overall_objective=f"Master skills: {', '.join(target_skills)}",
            milestones=sequenced_milestones,
            estimated_duration_days=estimated_duration,
            current_position=0,
            completion_percentage=0.0,
            adaptive_adjustments=[],
            personalization_factors={
                "learning_style": learning_preferences.primary_learning_style.value,
                "feedback_style": learning_preferences.preferred_feedback_style.value,
                "difficulty_progression": learning_preferences.preferred_difficulty_progression,
                "session_length": learning_preferences.optimal_session_length,
                "variety_preference": learning_preferences.challenge_variety_preference
            },
            creation_date=datetime.now().isoformat()
        )

        self.logger.info(f"✅ Generated pathway with {len(sequenced_milestones)} milestones, "
                        f"estimated duration: {estimated_duration} days")

        return pathway

    def _create_personalized_milestones(self, agent_profile: AgentProfile,
                                      learning_preferences: LearningPreferences,
                                      target_skills: List[str]) -> List[PersonalizedMilestone]:
        """Create personalized milestones for target skills"""
        milestones = []

        for i, skill in enumerate(target_skills):
            current_level = agent_profile.skill_levels.get(skill, 0.3)
            target_level = 0.8  # Target proficiency

            # Create milestone with personalized elements
            milestone = PersonalizedMilestone(
                milestone_id=f"milestone_{skill}_{i}",
                agent_id=agent_profile.agent_id,
                skill_focus=skill,
                title=self._create_personalized_title(skill, learning_preferences),
                description=self._create_personalized_description(skill, learning_preferences),
                target_proficiency=target_level,
                estimated_completion=self._estimate_milestone_completion(
                    current_level, target_level, learning_preferences
                ),
                prerequisite_milestones=self._get_prerequisite_milestones(skill, target_skills),
                success_criteria=self._create_personalized_success_criteria(
                    skill, target_level, learning_preferences
                ),
                rewards=self._design_personalized_rewards(skill, learning_preferences),
                personalized_guidance=self._create_personalized_guidance(
                    skill, learning_preferences, current_level
                ),
                adaptive_content=self._design_adaptive_content(skill, learning_preferences)
            )

            milestones.append(milestone)

        return milestones

    def _create_personalized_title(self, skill: str, preferences: LearningPreferences) -> str:
        """Create personalized milestone title"""
        style_titles = {
            LearningStyle.VISUAL: f"Visualize and Master {skill.replace('_', ' ').title()}",
            LearningStyle.KINESTHETIC: f"Hands-On {skill.replace('_', ' ').title()} Practice",
            LearningStyle.ANALYTICAL: f"Systematic {skill.replace('_', ' ').title()} Analysis",
            LearningStyle.INTUITIVE: f"Intuitive {skill.replace('_', ' ').title()} Understanding",
            LearningStyle.SEQUENTIAL: f"Step-by-Step {skill.replace('_', ' ').title()} Mastery",
            LearningStyle.GLOBAL: f"Comprehensive {skill.replace('_', ' ').title()} Context"
        }

        return style_titles.get(preferences.primary_learning_style,
                               f"Master {skill.replace('_', ' ').title()}")

    def _create_personalized_description(self, skill: str, preferences: LearningPreferences) -> str:
        """Create personalized milestone description"""
        base_descriptions = {
            "algorithms": "Master fundamental algorithmic concepts and implementations",
            "data_structures": "Learn to efficiently organize and manipulate data",
            "optimization": "Develop skills in code and performance optimization",
            "design_patterns": "Understand and apply software design patterns",
            "debugging": "Master systematic debugging and error resolution",
            "testing": "Learn comprehensive testing strategies and practices"
        }

        base_desc = base_descriptions.get(skill, f"Develop proficiency in {skill}")

        # Add learning style specific elements
        style_additions = {
            LearningStyle.VISUAL: " through visual examples and diagrams",
            LearningStyle.KINESTHETIC: " through hands-on practice and experimentation",
            LearningStyle.ANALYTICAL: " through systematic analysis and logical progression",
            LearningStyle.INTUITIVE: " by recognizing patterns and building intuition",
            LearningStyle.SEQUENTIAL: " with structured, step-by-step learning",
            LearningStyle.GLOBAL: " by understanding the broader context and connections"
        }

        addition = style_additions.get(preferences.primary_learning_style, "")
        return base_desc + addition

    def _estimate_milestone_completion(self, current_level: float, target_level: float,
                                     preferences: LearningPreferences) -> str:
        """Estimate milestone completion date"""
        skill_gap = target_level - current_level

        # Base learning rate adjusted for learning style and preferences
        base_days = max(1, int(skill_gap * 20))  # 20 days per skill level point

        # Adjust based on learning preferences
        if preferences.preferred_difficulty_progression == "steep":
            base_days = int(base_days * 0.8)  # Faster progression
        elif preferences.preferred_difficulty_progression == "gradual":
            base_days = int(base_days * 1.2)  # Slower, more thorough

        completion_date = datetime.now() + timedelta(days=base_days)
        return completion_date.isoformat()

    def _get_prerequisite_milestones(self, skill: str, all_target_skills: List[str]) -> List[str]:
        """Get prerequisite milestones for a skill"""
        prerequisites = self.skill_dependencies.get(skill, [])

        # Only include prerequisites that are in the target skills
        relevant_prereqs = [prereq for prereq in prerequisites if prereq in all_target_skills]

        return [f"milestone_{prereq}_0" for prereq in relevant_prereqs]  # Simplified milestone IDs

    def _create_personalized_success_criteria(self, skill: str, target_level: float,
                                            preferences: LearningPreferences) -> Dict[str, Any]:
        """Create personalized success criteria"""
        base_criteria = {
            "proficiency_level": target_level,
            "consistency_threshold": 0.8,
            "retention_period_days": 7
        }

        # Customize based on learning preferences
        if preferences.error_tolerance > 0.7:
            base_criteria["error_acceptance_rate"] = 0.3  # Allow more errors
        else:
            base_criteria["error_acceptance_rate"] = 0.1  # Stricter error tolerance

        if preferences.persistence_level > 0.8:
            base_criteria["challenge_completion_rate"] = 0.9  # High completion expectation
        else:
            base_criteria["challenge_completion_rate"] = 0.7  # More flexible

        # Add learning style specific criteria
        if preferences.primary_learning_style == LearningStyle.ANALYTICAL:
            base_criteria["explanation_quality_required"] = True
        elif preferences.primary_learning_style == LearningStyle.KINESTHETIC:
            base_criteria["practical_application_required"] = True

        return base_criteria

    def _design_personalized_rewards(self, skill: str, preferences: LearningPreferences) -> List[str]:
        """Design personalized rewards and recognition"""
        rewards = []

        # Base achievement recognition
        rewards.append(f"🏆 {skill.replace('_', ' ').title()} Proficiency Achievement")

        # Learning style specific rewards
        style_rewards = {
            LearningStyle.VISUAL: "📊 Visual mastery badge - your pattern recognition skills shine!",
            LearningStyle.KINESTHETIC: "🛠️ Hands-on expert badge - you've mastered through practice!",
            LearningStyle.ANALYTICAL: "🧮 Analytical thinker badge - your systematic approach paid off!",
            LearningStyle.INTUITIVE: "💡 Intuitive insight badge - your pattern recognition is exceptional!",
            LearningStyle.SEQUENTIAL: "📈 Methodical mastery badge - your step-by-step approach worked!",
            LearningStyle.GLOBAL: "🌐 Big-picture champion badge - you see the connections!"
        }

        style_reward = style_rewards.get(preferences.primary_learning_style)
        if style_reward:
            rewards.append(style_reward)

        # Persistence-based rewards
        if preferences.persistence_level > 0.7:
            rewards.append("🔥 Persistence champion - you never gave up!")

        return rewards

    def _create_personalized_guidance(self, skill: str, preferences: LearningPreferences,
                                    current_level: float) -> str:
        """Create personalized guidance for the milestone"""

        # Base guidance based on current skill level
        if current_level < 0.3:
            level_guidance = "Start with fundamental concepts and basic examples. "
        elif current_level < 0.6:
            level_guidance = "Build on your foundation with intermediate challenges. "
        else:
            level_guidance = "Push your limits with advanced applications. "

        # Learning style specific guidance
        style_guidance = {
            LearningStyle.VISUAL: "Look for visual representations, diagrams, and concrete examples. Create your own visual aids to reinforce learning.",
            LearningStyle.KINESTHETIC: "Focus on hands-on practice and experimentation. Try multiple approaches and learn from trial and error.",
            LearningStyle.ANALYTICAL: "Break down complex problems systematically. Understand the 'why' behind each concept before moving forward.",
            LearningStyle.INTUITIVE: "Look for patterns and connections. Trust your insights and explore creative solutions.",
            LearningStyle.SEQUENTIAL: "Follow a structured learning path. Master each prerequisite thoroughly before advancing.",
            LearningStyle.GLOBAL: "Understand how this skill fits into the bigger picture. See connections to other concepts and real-world applications."
        }

        style_advice = style_guidance.get(preferences.primary_learning_style,
                                        "Adapt your learning approach to what works best for you.")

        return level_guidance + style_advice

    def _design_adaptive_content(self, skill: str, preferences: LearningPreferences) -> Dict[str, Any]:
        """Design adaptive content for the milestone"""
        content = {
            "challenge_types": [],
            "resource_recommendations": [],
            "interaction_modes": [],
            "assessment_methods": []
        }

        # Learning style specific content
        if preferences.primary_learning_style == LearningStyle.VISUAL:
            content["challenge_types"].extend(["visualization_problems", "diagram_based_challenges"])
            content["resource_recommendations"].extend(["visual_tutorials", "infographics"])
            content["interaction_modes"].append("visual_feedback")

        elif preferences.primary_learning_style == LearningStyle.KINESTHETIC:
            content["challenge_types"].extend(["hands_on_coding", "implementation_focused"])
            content["resource_recommendations"].extend(["interactive_tutorials", "coding_exercises"])
            content["interaction_modes"].append("trial_and_error_encouraged")

        elif preferences.primary_learning_style == LearningStyle.ANALYTICAL:
            content["challenge_types"].extend(["algorithm_analysis", "complexity_problems"])
            content["resource_recommendations"].extend(["detailed_explanations", "theory_resources"])
            content["interaction_modes"].append("step_by_step_guidance")

        # Feedback style adaptations
        if preferences.preferred_feedback_style == FeedbackStyle.DETAILED:
            content["assessment_methods"].append("comprehensive_explanations")
        elif preferences.preferred_feedback_style == FeedbackStyle.EXAMPLE_BASED:
            content["assessment_methods"].append("example_driven_feedback")
        elif preferences.preferred_feedback_style == FeedbackStyle.ENCOURAGING:
            content["interaction_modes"].append("positive_reinforcement")

        # Difficulty progression adaptations
        content["progression_style"] = preferences.preferred_difficulty_progression
        content["variety_level"] = preferences.challenge_variety_preference

        return content

    def _sequence_milestones(self, milestones: List[PersonalizedMilestone],
                           preferences: LearningPreferences) -> List[PersonalizedMilestone]:
        """Sequence milestones based on dependencies and learning preferences"""

        # Create dependency graph
        milestone_deps = {m.milestone_id: m.prerequisite_milestones for m in milestones}

        # Topological sort with preference-based ordering
        sequenced = []
        remaining = milestones[:]

        while remaining:
            # Find milestones with satisfied prerequisites
            available = []
            for milestone in remaining:
                prereqs_satisfied = all(prereq in [m.milestone_id for m in sequenced]
                                      for prereq in milestone.prerequisite_milestones)
                if prereqs_satisfied:
                    available.append(milestone)

            if not available:
                # Circular dependency or error - take first remaining
                available = [remaining[0]]

            # Choose based on learning preferences
            if preferences.preferred_difficulty_progression == "gradual":
                # Pick easiest available (lowest current skill level)
                next_milestone = min(available, key=lambda m: len(m.prerequisite_milestones))
            elif preferences.preferred_difficulty_progression == "steep":
                # Pick most challenging available
                next_milestone = max(available, key=lambda m: len(m.prerequisite_milestones))
            else:  # mixed
                # Random selection for variety
                next_milestone = random.choice(available)

            sequenced.append(next_milestone)
            remaining.remove(next_milestone)

        return sequenced

    def _estimate_pathway_duration(self, milestones: List[PersonalizedMilestone],
                                 preferences: LearningPreferences,
                                 time_constraint: Optional[int]) -> int:
        """Estimate total pathway duration"""

        # Sum individual milestone durations
        milestone_days = []
        for milestone in milestones:
            completion_date = datetime.fromisoformat(milestone.estimated_completion)
            days_from_now = (completion_date - datetime.now()).days
            milestone_days.append(max(1, days_from_now))

        total_days = sum(milestone_days)

        # Adjust for parallel learning opportunities
        if preferences.challenge_variety_preference > 0.7:
            # Can handle multiple skills simultaneously
            total_days = int(total_days * 0.8)

        # Apply time constraints if specified
        if time_constraint and total_days > time_constraint:
            # Would need to implement time-constrained optimization
            total_days = time_constraint
            self.logger.warning(f"⚠️ Pathway compressed to meet time constraint: {time_constraint} days")

        return total_days

    def adapt_pathway_based_on_progress(self, pathway: LearningPathway,
                                      recent_attempts: List[ChallengeAttempt],
                                      performance_data: Dict[str, Any]) -> LearningPathway:
        """Adapt pathway based on actual learning progress"""

        self.logger.info(f"🔄 Adapting pathway {pathway.pathway_id} based on progress")

        adaptations = []

        # Analyze recent performance
        if recent_attempts:
            recent_success_rate = np.mean([1.0 if a.success else 0.0 for a in recent_attempts])

            if recent_success_rate < 0.3:
                # Struggling - make adjustments
                adaptations.append("reduced_difficulty_due_to_struggles")

                # Add additional support milestones
                current_milestone = pathway.milestones[pathway.current_position]
                support_milestone = PersonalizedMilestone(
                    milestone_id=f"{current_milestone.milestone_id}_support",
                    agent_id=pathway.agent_id,
                    skill_focus=current_milestone.skill_focus,
                    title=f"Foundation Support for {current_milestone.title}",
                    description="Additional practice and foundation building",
                    target_proficiency=current_milestone.target_proficiency * 0.7,
                    estimated_completion=(datetime.now() + timedelta(days=7)).isoformat(),
                    prerequisite_milestones=[],
                    success_criteria={"proficiency_level": 0.5},
                    rewards=["🎯 Foundation builder badge"],
                    personalized_guidance="Take time to build a solid foundation.",
                    adaptive_content={"extra_practice": True}
                )

                # Insert support milestone
                pathway.milestones.insert(pathway.current_position, support_milestone)

            elif recent_success_rate > 0.8:
                # Excelling - accelerate or add challenges
                adaptations.append("accelerated_due_to_excellence")

                # Reduce estimated durations
                for milestone in pathway.milestones[pathway.current_position:]:
                    completion_date = datetime.fromisoformat(milestone.estimated_completion)
                    new_date = completion_date - timedelta(days=3)
                    milestone.estimated_completion = new_date.isoformat()

        # Update pathway
        pathway.adaptive_adjustments.extend(adaptations)

        # Recalculate completion percentage
        completed_milestones = pathway.current_position
        total_milestones = len(pathway.milestones)
        pathway.completion_percentage = (completed_milestones / total_milestones) * 100 if total_milestones > 0 else 0

        self.logger.info(f"✅ Applied {len(adaptations)} adaptations to pathway")

        return pathway

    def generate_personalized_challenge(self, base_challenge: Challenge,
                                      preferences: LearningPreferences,
                                      current_skill_level: float) -> PersonalizedChallenge:
        """Generate a personalized version of a challenge"""

        personalized_elements = {}
        learning_style_adaptations = []
        feedback_customizations = {}
        difficulty_adjustments = {}
        motivational_elements = []

        # Learning style adaptations
        if preferences.primary_learning_style == LearningStyle.VISUAL:
            learning_style_adaptations.extend([
                "add_visual_examples",
                "include_diagram_hints",
                "provide_step_visualization"
            ])
            personalized_elements["visual_aids"] = True

        elif preferences.primary_learning_style == LearningStyle.KINESTHETIC:
            learning_style_adaptations.extend([
                "encourage_experimentation",
                "provide_multiple_approaches",
                "allow_trial_and_error"
            ])
            personalized_elements["experimentation_encouraged"] = True

        elif preferences.primary_learning_style == LearningStyle.ANALYTICAL:
            learning_style_adaptations.extend([
                "provide_detailed_explanations",
                "break_down_steps",
                "explain_reasoning"
            ])
            personalized_elements["detailed_reasoning"] = True

        # Feedback customizations
        feedback_customizations["style"] = preferences.preferred_feedback_style.value

        if preferences.preferred_feedback_style == FeedbackStyle.ENCOURAGING:
            feedback_customizations["positive_framing"] = True
            feedback_customizations["celebrate_progress"] = True

        elif preferences.preferred_feedback_style == FeedbackStyle.DETAILED:
            feedback_customizations["comprehensive_explanations"] = True
            feedback_customizations["include_examples"] = True

        # Difficulty adjustments
        if current_skill_level < 0.4:
            difficulty_adjustments["provide_more_hints"] = 0.3
            difficulty_adjustments["simplify_requirements"] = 0.2

        elif current_skill_level > 0.8:
            difficulty_adjustments["add_constraints"] = 0.2
            difficulty_adjustments["increase_complexity"] = 0.3

        # Motivational elements
        if preferences.persistence_level < 0.5:
            motivational_elements.extend([
                "break_into_smaller_steps",
                "provide_frequent_encouragement",
                "celebrate_small_wins"
            ])

        if preferences.curiosity_drive > 0.7:
            motivational_elements.extend([
                "provide_exploration_opportunities",
                "suggest_creative_extensions",
                "connect_to_broader_concepts"
            ])

        return PersonalizedChallenge(
            base_challenge=base_challenge,
            personalized_elements=personalized_elements,
            learning_style_adaptations=learning_style_adaptations,
            feedback_customizations=feedback_customizations,
            difficulty_adjustments=difficulty_adjustments,
            motivational_elements=motivational_elements
        )