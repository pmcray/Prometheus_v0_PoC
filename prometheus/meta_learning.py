"""
Meta-Learning Optimization System v0.63
Implementation of meta-learning capabilities that learn how to learn more effectively
by analyzing patterns across different learning scenarios and optimizing the learning process itself.
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import pickle
from pathlib import Path
import copy
import statistics
from collections import defaultdict, deque
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetaLearningStrategy(Enum):
    MAML = "model_agnostic_meta_learning"
    REPTILE = "reptile"
    GRADIENT_EPISODIC_MEMORY = "gem"
    ELASTIC_WEIGHT_CONSOLIDATION = "ewc"
    META_SGD = "meta_sgd"
    LEARNING_TO_LEARN = "l2l"
    NEURAL_ARCHITECTURE_SEARCH = "nas"
    HYPERPARAMETER_OPTIMIZATION = "hpo"


class LearningPhase(Enum):
    EXPLORATION = "exploration"
    EXPLOITATION = "exploitation"
    CONSOLIDATION = "consolidation"
    TRANSFER = "transfer"
    ADAPTATION = "adaptation"


class MetaKnowledgeType(Enum):
    LEARNING_PATTERNS = "learning_patterns"
    OPTIMIZATION_STRATEGIES = "optimization_strategies"
    TRANSFER_RULES = "transfer_rules"
    HYPERPARAMETER_CONFIGS = "hyperparameter_configs"
    ARCHITECTURE_PATTERNS = "architecture_patterns"
    CURRICULUM_SEQUENCES = "curriculum_sequences"
    FAILURE_MODES = "failure_modes"
    SUCCESS_FACTORS = "success_factors"


@dataclass
class LearningEpisode:
    episode_id: str
    task_type: str
    task_description: str
    agent_id: str
    initial_performance: float
    final_performance: float
    learning_duration: timedelta
    hyperparameters: Dict[str, Any]
    learning_curve: List[Tuple[datetime, float]]
    strategies_used: List[str]
    transfer_source: Optional[str] = None
    success_metrics: Dict[str, float] = field(default_factory=dict)
    failure_points: List[str] = field(default_factory=list)
    meta_features: Dict[str, Any] = field(default_factory=dict)
    contextual_factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaKnowledge:
    knowledge_id: str
    knowledge_type: MetaKnowledgeType
    pattern_description: str
    applicability_conditions: Dict[str, Any]
    effectiveness_score: float
    confidence_level: float
    usage_count: int = 0
    success_rate: float = 0.0
    discovery_episodes: List[str] = field(default_factory=list)
    validation_episodes: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class MetaLearningModel:
    model_id: str
    model_type: str
    architecture: Dict[str, Any]
    parameters: Dict[str, Any]
    training_history: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    adaptation_speed: float = 0.0
    generalization_score: float = 0.0
    transfer_efficiency: float = 0.0


class MetaFeatureExtractor:
    def __init__(self):
        self.feature_extractors = {
            'task_complexity': self._extract_task_complexity,
            'learning_dynamics': self._extract_learning_dynamics,
            'agent_characteristics': self._extract_agent_characteristics,
            'contextual_factors': self._extract_contextual_factors,
            'temporal_patterns': self._extract_temporal_patterns
        }

    def extract_features(self, episode: LearningEpisode) -> Dict[str, Any]:
        features = {}
        for feature_type, extractor in self.feature_extractors.items():
            try:
                features[feature_type] = extractor(episode)
            except Exception as e:
                logger.warning(f"Failed to extract {feature_type}: {e}")
                features[feature_type] = {}
        return features

    def _extract_task_complexity(self, episode: LearningEpisode) -> Dict[str, float]:
        return {
            'performance_gap': episode.final_performance - episode.initial_performance,
            'learning_duration_hours': episode.learning_duration.total_seconds() / 3600,
            'curve_steepness': self._calculate_curve_steepness(episode.learning_curve),
            'plateau_frequency': self._calculate_plateau_frequency(episode.learning_curve),
            'variance': self._calculate_performance_variance(episode.learning_curve)
        }

    def _extract_learning_dynamics(self, episode: LearningEpisode) -> Dict[str, float]:
        curve = episode.learning_curve
        if len(curve) < 3:
            return {}

        performances = [point[1] for point in curve]
        return {
            'initial_velocity': self._calculate_initial_velocity(performances),
            'acceleration': self._calculate_acceleration(performances),
            'convergence_rate': self._calculate_convergence_rate(performances),
            'stability': self._calculate_stability(performances),
            'overfitting_risk': self._calculate_overfitting_risk(performances)
        }

    def _extract_agent_characteristics(self, episode: LearningEpisode) -> Dict[str, Any]:
        return {
            'agent_type': episode.agent_id.split('_')[0] if '_' in episode.agent_id else 'unknown',
            'baseline_performance': episode.initial_performance,
            'learning_capacity': episode.final_performance - episode.initial_performance,
            'adaptation_speed': len(episode.learning_curve) / episode.learning_duration.total_seconds()
        }

    def _extract_contextual_factors(self, episode: LearningEpisode) -> Dict[str, Any]:
        factors = episode.contextual_factors.copy()
        factors.update({
            'has_transfer': episode.transfer_source is not None,
            'strategy_diversity': len(set(episode.strategies_used)),
            'hyperparameter_count': len(episode.hyperparameters)
        })
        return factors

    def _extract_temporal_patterns(self, episode: LearningEpisode) -> Dict[str, float]:
        if len(episode.learning_curve) < 2:
            return {}

        timestamps = [point[0] for point in episode.learning_curve]
        intervals = [(timestamps[i+1] - timestamps[i]).total_seconds()
                    for i in range(len(timestamps)-1)]

        return {
            'update_frequency': len(intervals) / episode.learning_duration.total_seconds(),
            'interval_consistency': 1.0 / (1.0 + np.std(intervals)) if intervals else 0.0,
            'temporal_density': len(episode.learning_curve) / episode.learning_duration.total_seconds()
        }

    def _calculate_curve_steepness(self, curve: List[Tuple[datetime, float]]) -> float:
        if len(curve) < 2:
            return 0.0

        performances = [point[1] for point in curve]
        max_diff = max(abs(performances[i+1] - performances[i])
                      for i in range(len(performances)-1))
        return max_diff

    def _calculate_plateau_frequency(self, curve: List[Tuple[datetime, float]]) -> float:
        if len(curve) < 3:
            return 0.0

        performances = [point[1] for point in curve]
        plateaus = 0
        threshold = 0.01

        for i in range(1, len(performances)-1):
            if (abs(performances[i] - performances[i-1]) < threshold and
                abs(performances[i+1] - performances[i]) < threshold):
                plateaus += 1

        return plateaus / len(performances)

    def _calculate_performance_variance(self, curve: List[Tuple[datetime, float]]) -> float:
        performances = [point[1] for point in curve]
        return np.var(performances) if len(performances) > 1 else 0.0

    def _calculate_initial_velocity(self, performances: List[float]) -> float:
        if len(performances) < 2:
            return 0.0
        return performances[1] - performances[0]

    def _calculate_acceleration(self, performances: List[float]) -> float:
        if len(performances) < 3:
            return 0.0

        velocities = [performances[i+1] - performances[i]
                     for i in range(len(performances)-1)]
        return velocities[1] - velocities[0] if len(velocities) >= 2 else 0.0

    def _calculate_convergence_rate(self, performances: List[float]) -> float:
        if len(performances) < 2:
            return 0.0

        final_performance = performances[-1]
        convergence_threshold = 0.95 * final_performance

        for i, perf in enumerate(performances):
            if perf >= convergence_threshold:
                return i / len(performances)

        return 1.0

    def _calculate_stability(self, performances: List[float]) -> float:
        if len(performances) < 2:
            return 1.0

        changes = [abs(performances[i+1] - performances[i])
                  for i in range(len(performances)-1)]
        avg_change = np.mean(changes)
        return 1.0 / (1.0 + avg_change)

    def _calculate_overfitting_risk(self, performances: List[float]) -> float:
        if len(performances) < 10:
            return 0.0

        mid_point = len(performances) // 2
        early_avg = np.mean(performances[:mid_point])
        late_avg = np.mean(performances[mid_point:])

        if early_avg > late_avg:
            return (early_avg - late_avg) / early_avg
        return 0.0


class MetaPatternRecognizer:
    def __init__(self):
        self.pattern_templates = {
            'rapid_learner': {
                'conditions': {
                    'learning_dynamics.initial_velocity': ('>', 0.1),
                    'learning_dynamics.convergence_rate': ('<', 0.3)
                },
                'recommendations': ['use_aggressive_learning_rates', 'early_stopping']
            },
            'slow_starter': {
                'conditions': {
                    'learning_dynamics.initial_velocity': ('<', 0.01),
                    'task_complexity.performance_gap': ('>', 0.5)
                },
                'recommendations': ['warm_up_schedule', 'curriculum_learning']
            },
            'plateau_prone': {
                'conditions': {
                    'task_complexity.plateau_frequency': ('>', 0.3),
                    'learning_dynamics.stability': ('>', 0.8)
                },
                'recommendations': ['learning_rate_scheduling', 'exploration_boost']
            },
            'transfer_beneficial': {
                'conditions': {
                    'contextual_factors.has_transfer': ('==', True),
                    'task_complexity.performance_gap': ('>', 0.3)
                },
                'recommendations': ['fine_tuning', 'feature_extraction']
            }
        }

    def recognize_patterns(self, episode_features: Dict[str, Any]) -> List[Dict[str, Any]]:
        recognized_patterns = []

        for pattern_name, template in self.pattern_templates.items():
            if self._matches_template(episode_features, template['conditions']):
                recognized_patterns.append({
                    'pattern_name': pattern_name,
                    'confidence': self._calculate_pattern_confidence(
                        episode_features, template['conditions']
                    ),
                    'recommendations': template['recommendations']
                })

        return sorted(recognized_patterns, key=lambda x: x['confidence'], reverse=True)

    def _matches_template(self, features: Dict[str, Any], conditions: Dict[str, Tuple]) -> bool:
        for feature_path, (operator, threshold) in conditions.items():
            value = self._get_nested_value(features, feature_path)
            if value is None:
                continue

            if operator == '>' and value <= threshold:
                return False
            elif operator == '<' and value >= threshold:
                return False
            elif operator == '==' and value != threshold:
                return False
            elif operator == '>=' and value < threshold:
                return False
            elif operator == '<=' and value > threshold:
                return False

        return True

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Optional[Any]:
        keys = path.split('.')
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _calculate_pattern_confidence(self, features: Dict[str, Any],
                                    conditions: Dict[str, Tuple]) -> float:
        total_conditions = len(conditions)
        if total_conditions == 0:
            return 0.0

        confidence_sum = 0.0

        for feature_path, (operator, threshold) in conditions.items():
            value = self._get_nested_value(features, feature_path)
            if value is None:
                continue

            condition_confidence = self._calculate_condition_confidence(
                value, operator, threshold
            )
            confidence_sum += condition_confidence

        return confidence_sum / total_conditions

    def _calculate_condition_confidence(self, value: float, operator: str,
                                      threshold: float) -> float:
        if operator == '>':
            return min(1.0, max(0.0, (value - threshold) / threshold)) if threshold > 0 else 0.0
        elif operator == '<':
            return min(1.0, max(0.0, (threshold - value) / threshold)) if threshold > 0 else 0.0
        elif operator == '==':
            return 1.0 if value == threshold else 0.0
        elif operator == '>=':
            return 1.0 if value >= threshold else 0.0
        elif operator == '<=':
            return 1.0 if value <= threshold else 0.0

        return 0.0


class MetaOptimizer:
    def __init__(self):
        self.optimization_strategies = {
            'hyperparameter_optimization': self._optimize_hyperparameters,
            'architecture_search': self._optimize_architecture,
            'learning_schedule': self._optimize_learning_schedule,
            'transfer_strategy': self._optimize_transfer_strategy,
            'regularization': self._optimize_regularization
        }
        self.optimization_history = []

    def optimize_learning_process(self, historical_episodes: List[LearningEpisode],
                                 target_task_characteristics: Dict[str, Any],
                                 optimization_budget: int = 100) -> Dict[str, Any]:

        optimization_results = {}

        # Analyze historical performance patterns
        performance_analysis = self._analyze_historical_performance(historical_episodes)

        # Identify best practices from successful episodes
        best_practices = self._extract_best_practices(historical_episodes)

        # Generate optimization recommendations
        recommendations = self._generate_optimization_recommendations(
            performance_analysis, best_practices, target_task_characteristics
        )

        # Execute optimization strategies within budget
        optimization_results = self._execute_optimization_strategies(
            recommendations, optimization_budget
        )

        return {
            'optimization_results': optimization_results,
            'best_practices': best_practices,
            'recommendations': recommendations,
            'confidence': self._calculate_optimization_confidence(optimization_results)
        }

    def _analyze_historical_performance(self, episodes: List[LearningEpisode]) -> Dict[str, Any]:
        if not episodes:
            return {}

        performance_gains = [ep.final_performance - ep.initial_performance for ep in episodes]
        learning_times = [ep.learning_duration.total_seconds() for ep in episodes]

        return {
            'avg_performance_gain': np.mean(performance_gains),
            'std_performance_gain': np.std(performance_gains),
            'avg_learning_time': np.mean(learning_times),
            'success_rate': len([ep for ep in episodes if ep.final_performance > ep.initial_performance]) / len(episodes),
            'best_episode': max(episodes, key=lambda ep: ep.final_performance - ep.initial_performance),
            'worst_episode': min(episodes, key=lambda ep: ep.final_performance - ep.initial_performance)
        }

    def _extract_best_practices(self, episodes: List[LearningEpisode]) -> Dict[str, Any]:
        # Sort episodes by performance gain
        sorted_episodes = sorted(episodes,
                               key=lambda ep: ep.final_performance - ep.initial_performance,
                               reverse=True)

        top_20_percent = sorted_episodes[:max(1, len(sorted_episodes) // 5)]

        # Extract common patterns from top performers
        common_hyperparameters = self._find_common_hyperparameters(top_20_percent)
        common_strategies = self._find_common_strategies(top_20_percent)
        success_factors = self._identify_success_factors(top_20_percent)

        return {
            'top_hyperparameters': common_hyperparameters,
            'effective_strategies': common_strategies,
            'success_factors': success_factors,
            'sample_size': len(top_20_percent)
        }

    def _generate_optimization_recommendations(self,
                                             performance_analysis: Dict[str, Any],
                                             best_practices: Dict[str, Any],
                                             target_characteristics: Dict[str, Any]) -> List[Dict[str, Any]]:
        recommendations = []

        # Hyperparameter recommendations
        if 'top_hyperparameters' in best_practices:
            recommendations.append({
                'type': 'hyperparameter_optimization',
                'priority': 0.9,
                'suggestions': best_practices['top_hyperparameters'],
                'reasoning': 'Based on top performing episodes'
            })

        # Strategy recommendations
        if 'effective_strategies' in best_practices:
            recommendations.append({
                'type': 'strategy_selection',
                'priority': 0.8,
                'suggestions': best_practices['effective_strategies'],
                'reasoning': 'Strategies from successful learning episodes'
            })

        # Learning schedule recommendations
        avg_time = performance_analysis.get('avg_learning_time', 3600)
        recommendations.append({
            'type': 'learning_schedule',
            'priority': 0.7,
            'suggestions': {
                'max_training_time': avg_time * 1.2,
                'early_stopping_patience': max(10, int(avg_time / 360)),
                'checkpoint_frequency': max(1, int(avg_time / 1800))
            },
            'reasoning': 'Optimized based on historical learning times'
        })

        return sorted(recommendations, key=lambda x: x['priority'], reverse=True)

    def _execute_optimization_strategies(self, recommendations: List[Dict[str, Any]],
                                       budget: int) -> Dict[str, Any]:
        executed_optimizations = {}
        budget_used = 0

        for rec in recommendations:
            if budget_used >= budget:
                break

            strategy_type = rec['type']
            if strategy_type in self.optimization_strategies:
                try:
                    result = self.optimization_strategies[strategy_type](
                        rec['suggestions'], min(budget - budget_used, budget // len(recommendations))
                    )
                    executed_optimizations[strategy_type] = result
                    budget_used += result.get('budget_used', 0)
                except Exception as e:
                    logger.warning(f"Failed to execute {strategy_type}: {e}")

        return executed_optimizations

    def _optimize_hyperparameters(self, suggestions: Dict[str, Any], budget: int) -> Dict[str, Any]:
        # Simplified hyperparameter optimization
        optimized_params = {}

        for param_name, param_value in suggestions.items():
            if isinstance(param_value, (int, float)):
                # Add some random variation for exploration
                noise = np.random.normal(0, 0.1) * param_value
                optimized_params[param_name] = param_value + noise
            else:
                optimized_params[param_name] = param_value

        return {
            'optimized_parameters': optimized_params,
            'budget_used': min(budget, 20),
            'confidence': 0.8
        }

    def _optimize_architecture(self, suggestions: Dict[str, Any], budget: int) -> Dict[str, Any]:
        # Simplified architecture optimization
        return {
            'architecture_changes': {
                'layer_modifications': 'adaptive_depth',
                'activation_functions': 'mixed_activations',
                'regularization': 'adaptive_dropout'
            },
            'budget_used': min(budget, 30),
            'confidence': 0.7
        }

    def _optimize_learning_schedule(self, suggestions: Dict[str, Any], budget: int) -> Dict[str, Any]:
        return {
            'schedule_modifications': suggestions,
            'budget_used': min(budget, 10),
            'confidence': 0.9
        }

    def _optimize_transfer_strategy(self, suggestions: Dict[str, Any], budget: int) -> Dict[str, Any]:
        return {
            'transfer_recommendations': {
                'source_selection': 'similarity_based',
                'transfer_method': 'fine_tuning',
                'layer_freezing': 'adaptive'
            },
            'budget_used': min(budget, 15),
            'confidence': 0.75
        }

    def _optimize_regularization(self, suggestions: Dict[str, Any], budget: int) -> Dict[str, Any]:
        return {
            'regularization_config': {
                'l1_penalty': 0.001,
                'l2_penalty': 0.01,
                'dropout_rate': 0.3,
                'batch_normalization': True
            },
            'budget_used': min(budget, 15),
            'confidence': 0.8
        }

    def _find_common_hyperparameters(self, episodes: List[LearningEpisode]) -> Dict[str, Any]:
        param_values = defaultdict(list)

        for episode in episodes:
            for param_name, param_value in episode.hyperparameters.items():
                param_values[param_name].append(param_value)

        common_params = {}
        for param_name, values in param_values.items():
            if len(values) >= len(episodes) * 0.5:  # Present in at least 50% of episodes
                if all(isinstance(v, (int, float)) for v in values):
                    common_params[param_name] = np.mean(values)
                else:
                    # For non-numeric values, take the most common
                    from collections import Counter
                    common_params[param_name] = Counter(values).most_common(1)[0][0]

        return common_params

    def _find_common_strategies(self, episodes: List[LearningEpisode]) -> List[str]:
        strategy_counts = defaultdict(int)

        for episode in episodes:
            for strategy in episode.strategies_used:
                strategy_counts[strategy] += 1

        # Return strategies used in at least 30% of top episodes
        threshold = len(episodes) * 0.3
        return [strategy for strategy, count in strategy_counts.items() if count >= threshold]

    def _identify_success_factors(self, episodes: List[LearningEpisode]) -> Dict[str, Any]:
        success_factors = {
            'avg_duration': np.mean([ep.learning_duration.total_seconds() for ep in episodes]),
            'common_failure_points': [],
            'performance_characteristics': {}
        }

        # Analyze failure points to identify what to avoid
        all_failure_points = []
        for episode in episodes:
            all_failure_points.extend(episode.failure_points)

        if all_failure_points:
            from collections import Counter
            common_failures = Counter(all_failure_points).most_common(3)
            success_factors['common_failure_points'] = [failure[0] for failure in common_failures]

        return success_factors

    def _calculate_optimization_confidence(self, optimization_results: Dict[str, Any]) -> float:
        if not optimization_results:
            return 0.0

        confidences = []
        for result in optimization_results.values():
            if isinstance(result, dict) and 'confidence' in result:
                confidences.append(result['confidence'])

        return np.mean(confidences) if confidences else 0.5


class MetaLearningOrchestrator:
    def __init__(self, storage_path: str = "meta_learning_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        self.feature_extractor = MetaFeatureExtractor()
        self.pattern_recognizer = MetaPatternRecognizer()
        self.meta_optimizer = MetaOptimizer()

        self.episode_history: List[LearningEpisode] = []
        self.meta_knowledge_base: Dict[str, MetaKnowledge] = {}
        self.meta_models: Dict[str, MetaLearningModel] = {}

        self.load_persistent_data()

    async def learn_from_episode(self, episode: LearningEpisode) -> Dict[str, Any]:
        """Process a learning episode and extract meta-knowledge"""

        # Extract features from the episode
        episode_features = self.feature_extractor.extract_features(episode)
        episode.meta_features = episode_features

        # Recognize patterns in the episode
        recognized_patterns = self.pattern_recognizer.recognize_patterns(episode_features)

        # Update meta-knowledge base
        meta_knowledge_updates = await self._update_meta_knowledge(episode, recognized_patterns)

        # Store the episode
        self.episode_history.append(episode)

        # Update meta-models if enough data is available
        if len(self.episode_history) >= 10:
            await self._update_meta_models()

        # Save persistent data
        self.save_persistent_data()

        return {
            'episode_id': episode.episode_id,
            'extracted_features': episode_features,
            'recognized_patterns': recognized_patterns,
            'meta_knowledge_updates': meta_knowledge_updates,
            'total_episodes': len(self.episode_history)
        }

    async def optimize_learning_strategy(self,
                                       target_task_type: str,
                                       agent_characteristics: Dict[str, Any],
                                       constraints: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate optimized learning strategy for a new task"""

        # Filter relevant historical episodes
        relevant_episodes = self._filter_relevant_episodes(target_task_type, agent_characteristics)

        if not relevant_episodes:
            return self._generate_default_strategy(target_task_type, agent_characteristics)

        # Extract target task characteristics
        target_characteristics = {
            'task_type': target_task_type,
            'agent_characteristics': agent_characteristics,
            'constraints': constraints or {}
        }

        # Generate optimization recommendations
        optimization_result = self.meta_optimizer.optimize_learning_process(
            relevant_episodes, target_characteristics
        )

        # Apply meta-knowledge recommendations
        meta_recommendations = self._apply_meta_knowledge(target_characteristics)

        # Combine and prioritize recommendations
        combined_strategy = self._combine_recommendations(
            optimization_result, meta_recommendations
        )

        return combined_strategy

    async def evaluate_learning_performance(self, episode: LearningEpisode) -> Dict[str, Any]:
        """Evaluate how well a learning episode performed compared to expectations"""

        # Find similar historical episodes for comparison
        similar_episodes = self._find_similar_episodes(episode)

        if not similar_episodes:
            return {'evaluation': 'insufficient_data', 'baseline_comparison': None}

        # Calculate performance metrics relative to similar episodes
        performance_evaluation = self._calculate_relative_performance(episode, similar_episodes)

        # Identify improvement opportunities
        improvement_opportunities = self._identify_improvement_opportunities(
            episode, similar_episodes
        )

        # Update meta-knowledge based on performance
        await self._update_performance_knowledge(episode, performance_evaluation)

        return {
            'relative_performance': performance_evaluation,
            'improvement_opportunities': improvement_opportunities,
            'baseline_episodes': len(similar_episodes),
            'confidence': min(1.0, len(similar_episodes) / 10.0)
        }

    def get_meta_insights(self) -> Dict[str, Any]:
        """Provide insights from accumulated meta-learning experience"""

        if not self.episode_history:
            return {'insights': 'insufficient_data'}

        # Analyze learning trends over time
        learning_trends = self._analyze_learning_trends()

        # Identify most effective strategies
        effective_strategies = self._identify_effective_strategies()

        # Analyze common failure modes
        failure_analysis = self._analyze_failure_modes()

        # Generate strategic recommendations
        strategic_recommendations = self._generate_strategic_recommendations()

        return {
            'total_episodes_analyzed': len(self.episode_history),
            'learning_trends': learning_trends,
            'effective_strategies': effective_strategies,
            'failure_analysis': failure_analysis,
            'strategic_recommendations': strategic_recommendations,
            'meta_knowledge_count': len(self.meta_knowledge_base),
            'meta_model_count': len(self.meta_models)
        }

    def _filter_relevant_episodes(self, target_task_type: str,
                                agent_characteristics: Dict[str, Any]) -> List[LearningEpisode]:
        relevant_episodes = []

        for episode in self.episode_history:
            relevance_score = 0.0

            # Task type similarity
            if episode.task_type == target_task_type:
                relevance_score += 0.5
            elif episode.task_type.split('_')[0] == target_task_type.split('_')[0]:
                relevance_score += 0.3

            # Agent similarity
            episode_agent_type = episode.agent_id.split('_')[0] if '_' in episode.agent_id else episode.agent_id
            target_agent_type = agent_characteristics.get('agent_type', '')

            if episode_agent_type == target_agent_type:
                relevance_score += 0.3

            # Performance threshold
            if episode.final_performance > episode.initial_performance:
                relevance_score += 0.2

            if relevance_score >= 0.5:
                relevant_episodes.append(episode)

        return sorted(relevant_episodes,
                     key=lambda ep: ep.final_performance - ep.initial_performance,
                     reverse=True)[:20]  # Top 20 most relevant

    def _generate_default_strategy(self, target_task_type: str,
                                 agent_characteristics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'strategy_type': 'default',
            'hyperparameters': {
                'learning_rate': 0.001,
                'batch_size': 32,
                'max_epochs': 100,
                'patience': 10
            },
            'recommendations': [
                'Use conservative learning settings',
                'Monitor performance closely',
                'Implement early stopping'
            ],
            'confidence': 0.3,
            'reasoning': 'Default strategy due to insufficient historical data'
        }

    async def _update_meta_knowledge(self, episode: LearningEpisode,
                                   patterns: List[Dict[str, Any]]) -> List[str]:
        updates = []

        for pattern in patterns:
            pattern_name = pattern['pattern_name']
            confidence = pattern['confidence']

            knowledge_id = f"{pattern_name}_{episode.task_type}"

            if knowledge_id in self.meta_knowledge_base:
                # Update existing knowledge
                knowledge = self.meta_knowledge_base[knowledge_id]
                knowledge.usage_count += 1
                knowledge.effectiveness_score = (
                    knowledge.effectiveness_score * 0.9 +
                    (episode.final_performance - episode.initial_performance) * 0.1
                )
                knowledge.confidence_level = (
                    knowledge.confidence_level * 0.9 + confidence * 0.1
                )
                knowledge.validation_episodes.append(episode.episode_id)
                knowledge.last_updated = datetime.now()
                updates.append(f"Updated knowledge: {knowledge_id}")
            else:
                # Create new knowledge
                new_knowledge = MetaKnowledge(
                    knowledge_id=knowledge_id,
                    knowledge_type=MetaKnowledgeType.LEARNING_PATTERNS,
                    pattern_description=f"Pattern: {pattern_name}",
                    applicability_conditions={'task_type': episode.task_type},
                    effectiveness_score=episode.final_performance - episode.initial_performance,
                    confidence_level=confidence,
                    usage_count=1,
                    discovery_episodes=[episode.episode_id]
                )
                self.meta_knowledge_base[knowledge_id] = new_knowledge
                updates.append(f"Created new knowledge: {knowledge_id}")

        return updates

    async def _update_meta_models(self):
        """Update meta-learning models based on accumulated experience"""

        # Create a simple meta-model that predicts learning outcomes
        recent_episodes = self.episode_history[-50:]  # Use recent episodes

        if len(recent_episodes) < 10:
            return

        # Extract features and outcomes for model training
        features = []
        outcomes = []

        for episode in recent_episodes:
            if episode.meta_features:
                feature_vector = self._flatten_features(episode.meta_features)
                outcome = episode.final_performance - episode.initial_performance
                features.append(feature_vector)
                outcomes.append(outcome)

        if len(features) >= 10:
            # Create a simple meta-model (placeholder for actual ML model)
            model_id = f"performance_predictor_{datetime.now().strftime('%Y%m%d')}"
            meta_model = MetaLearningModel(
                model_id=model_id,
                model_type="performance_predictor",
                architecture={'type': 'linear_regression'},
                parameters={'feature_count': len(features[0])},
                performance_metrics={
                    'training_episodes': len(features),
                    'feature_dimensionality': len(features[0]),
                    'outcome_variance': np.var(outcomes)
                }
            )

            self.meta_models[model_id] = meta_model

    def _flatten_features(self, features: Dict[str, Any]) -> List[float]:
        """Flatten nested feature dictionary into a vector"""
        flattened = []

        def _flatten_recursive(obj, prefix=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    _flatten_recursive(value, f"{prefix}_{key}" if prefix else key)
            elif isinstance(obj, (int, float)):
                flattened.append(float(obj))
            elif isinstance(obj, bool):
                flattened.append(1.0 if obj else 0.0)
            elif isinstance(obj, str):
                flattened.append(hash(obj) % 1000 / 1000.0)  # Simple string hashing

        _flatten_recursive(features)
        return flattened

    def _apply_meta_knowledge(self, target_characteristics: Dict[str, Any]) -> Dict[str, Any]:
        """Apply relevant meta-knowledge to generate recommendations"""

        applicable_knowledge = []

        for knowledge in self.meta_knowledge_base.values():
            if self._is_knowledge_applicable(knowledge, target_characteristics):
                applicable_knowledge.append(knowledge)

        if not applicable_knowledge:
            return {'recommendations': [], 'confidence': 0.0}

        # Sort by effectiveness and confidence
        applicable_knowledge.sort(
            key=lambda k: k.effectiveness_score * k.confidence_level,
            reverse=True
        )

        recommendations = []
        for knowledge in applicable_knowledge[:5]:  # Top 5 recommendations
            recommendations.append({
                'knowledge_id': knowledge.knowledge_id,
                'pattern': knowledge.pattern_description,
                'effectiveness': knowledge.effectiveness_score,
                'confidence': knowledge.confidence_level,
                'usage_count': knowledge.usage_count
            })

        return {
            'recommendations': recommendations,
            'confidence': np.mean([k.confidence_level for k in applicable_knowledge[:5]])
        }

    def _is_knowledge_applicable(self, knowledge: MetaKnowledge,
                               target_characteristics: Dict[str, Any]) -> bool:
        """Check if meta-knowledge is applicable to target characteristics"""

        conditions = knowledge.applicability_conditions

        for condition_key, condition_value in conditions.items():
            target_value = target_characteristics.get(condition_key)

            if target_value != condition_value:
                return False

        return True

    def _combine_recommendations(self, optimization_result: Dict[str, Any],
                               meta_recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Combine optimization and meta-knowledge recommendations"""

        combined_strategy = {
            'strategy_type': 'meta_optimized',
            'confidence': (
                optimization_result.get('confidence', 0.5) +
                meta_recommendations.get('confidence', 0.5)
            ) / 2,
            'optimization_results': optimization_result,
            'meta_knowledge_recommendations': meta_recommendations,
            'combined_recommendations': []
        }

        # Merge recommendations with priorities
        all_recommendations = []

        # Add optimization recommendations
        for rec in optimization_result.get('recommendations', []):
            all_recommendations.append({
                'source': 'optimization',
                'priority': rec.get('priority', 0.5),
                'content': rec
            })

        # Add meta-knowledge recommendations
        for rec in meta_recommendations.get('recommendations', []):
            all_recommendations.append({
                'source': 'meta_knowledge',
                'priority': rec.get('confidence', 0.5),
                'content': rec
            })

        # Sort by priority and combine
        all_recommendations.sort(key=lambda x: x['priority'], reverse=True)
        combined_strategy['combined_recommendations'] = all_recommendations[:10]

        return combined_strategy

    def _find_similar_episodes(self, target_episode: LearningEpisode) -> List[LearningEpisode]:
        """Find episodes similar to the target episode"""

        similar_episodes = []

        if not target_episode.meta_features:
            return similar_episodes

        target_features = self._flatten_features(target_episode.meta_features)

        for episode in self.episode_history:
            if episode.episode_id == target_episode.episode_id:
                continue

            if not episode.meta_features:
                continue

            episode_features = self._flatten_features(episode.meta_features)

            if len(episode_features) != len(target_features):
                continue

            # Calculate similarity (simple cosine similarity)
            similarity = self._calculate_cosine_similarity(target_features, episode_features)

            if similarity > 0.7:  # Threshold for similarity
                similar_episodes.append(episode)

        return similar_episodes

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""

        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _calculate_relative_performance(self, target_episode: LearningEpisode,
                                      similar_episodes: List[LearningEpisode]) -> Dict[str, Any]:
        """Calculate performance relative to similar episodes"""

        target_gain = target_episode.final_performance - target_episode.initial_performance
        similar_gains = [ep.final_performance - ep.initial_performance for ep in similar_episodes]

        percentile = (sum(1 for gain in similar_gains if gain < target_gain) /
                     len(similar_gains)) * 100

        return {
            'performance_gain': target_gain,
            'percentile_rank': percentile,
            'mean_similar_gain': np.mean(similar_gains),
            'std_similar_gain': np.std(similar_gains),
            'relative_performance': 'excellent' if percentile > 80 else
                                   'good' if percentile > 60 else
                                   'average' if percentile > 40 else
                                   'below_average'
        }

    def _identify_improvement_opportunities(self, target_episode: LearningEpisode,
                                          similar_episodes: List[LearningEpisode]) -> List[str]:
        """Identify opportunities for improvement based on similar episodes"""

        opportunities = []

        # Find better performing similar episodes
        better_episodes = [ep for ep in similar_episodes
                          if (ep.final_performance - ep.initial_performance) >
                             (target_episode.final_performance - target_episode.initial_performance)]

        if better_episodes:
            # Analyze what they did differently
            target_strategies = set(target_episode.strategies_used)
            better_strategies = []

            for episode in better_episodes:
                better_strategies.extend(episode.strategies_used)

            missing_strategies = set(better_strategies) - target_strategies
            if missing_strategies:
                opportunities.append(f"Consider using strategies: {', '.join(missing_strategies)}")

            # Compare hyperparameters
            target_params = target_episode.hyperparameters
            for episode in better_episodes[:3]:  # Top 3 better episodes
                for param, value in episode.hyperparameters.items():
                    if param in target_params and target_params[param] != value:
                        opportunities.append(f"Try {param} = {value} (used in better episode)")

        return opportunities[:5]  # Limit to top 5 opportunities

    async def _update_performance_knowledge(self, episode: LearningEpisode,
                                          performance_evaluation: Dict[str, Any]):
        """Update meta-knowledge based on performance evaluation"""

        performance_level = performance_evaluation['relative_performance']

        if performance_level in ['excellent', 'good']:
            # Extract successful patterns
            for strategy in episode.strategies_used:
                knowledge_id = f"successful_strategy_{strategy}"

                if knowledge_id in self.meta_knowledge_base:
                    self.meta_knowledge_base[knowledge_id].effectiveness_score += 0.1
                    self.meta_knowledge_base[knowledge_id].usage_count += 1
                else:
                    new_knowledge = MetaKnowledge(
                        knowledge_id=knowledge_id,
                        knowledge_type=MetaKnowledgeType.SUCCESS_FACTORS,
                        pattern_description=f"Successful strategy: {strategy}",
                        applicability_conditions={'strategy': strategy},
                        effectiveness_score=0.8,
                        confidence_level=0.7,
                        usage_count=1,
                        discovery_episodes=[episode.episode_id]
                    )
                    self.meta_knowledge_base[knowledge_id] = new_knowledge

    def _analyze_learning_trends(self) -> Dict[str, Any]:
        """Analyze trends in learning performance over time"""

        if len(self.episode_history) < 5:
            return {'trend': 'insufficient_data'}

        # Sort episodes by timestamp (assuming episode_id contains timestamp info)
        sorted_episodes = sorted(self.episode_history,
                               key=lambda ep: ep.episode_id)

        performance_gains = [ep.final_performance - ep.initial_performance
                           for ep in sorted_episodes]

        # Calculate trend using simple linear regression
        x = list(range(len(performance_gains)))
        y = performance_gains

        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            trend_direction = 'improving' if slope > 0.01 else 'declining' if slope < -0.01 else 'stable'
        else:
            trend_direction = 'stable'
            slope = 0

        return {
            'trend_direction': trend_direction,
            'trend_slope': slope,
            'recent_performance': np.mean(performance_gains[-5:]) if len(performance_gains) >= 5 else np.mean(performance_gains),
            'overall_performance': np.mean(performance_gains),
            'performance_variance': np.var(performance_gains)
        }

    def _identify_effective_strategies(self) -> Dict[str, Any]:
        """Identify the most effective learning strategies"""

        strategy_performance = defaultdict(list)

        for episode in self.episode_history:
            performance_gain = episode.final_performance - episode.initial_performance
            for strategy in episode.strategies_used:
                strategy_performance[strategy].append(performance_gain)

        strategy_effectiveness = {}
        for strategy, performances in strategy_performance.items():
            strategy_effectiveness[strategy] = {
                'avg_performance': np.mean(performances),
                'usage_count': len(performances),
                'success_rate': len([p for p in performances if p > 0]) / len(performances),
                'consistency': 1.0 / (1.0 + np.std(performances))
            }

        # Sort strategies by effectiveness
        sorted_strategies = sorted(strategy_effectiveness.items(),
                                 key=lambda x: x[1]['avg_performance'] * x[1]['success_rate'],
                                 reverse=True)

        return {
            'top_strategies': dict(sorted_strategies[:5]),
            'total_strategies_analyzed': len(strategy_effectiveness)
        }

    def _analyze_failure_modes(self) -> Dict[str, Any]:
        """Analyze common failure modes and their causes"""

        failure_analysis = {
            'common_failures': defaultdict(int),
            'failure_contexts': defaultdict(list),
            'failure_rate': 0.0
        }

        failed_episodes = [ep for ep in self.episode_history
                          if ep.final_performance <= ep.initial_performance]

        failure_analysis['failure_rate'] = len(failed_episodes) / len(self.episode_history)

        for episode in failed_episodes:
            for failure_point in episode.failure_points:
                failure_analysis['common_failures'][failure_point] += 1
                failure_analysis['failure_contexts'][failure_point].append({
                    'task_type': episode.task_type,
                    'strategies': episode.strategies_used,
                    'duration': episode.learning_duration.total_seconds()
                })

        # Convert to regular dict for JSON serialization
        failure_analysis['common_failures'] = dict(failure_analysis['common_failures'])
        failure_analysis['failure_contexts'] = dict(failure_analysis['failure_contexts'])

        return failure_analysis

    def _generate_strategic_recommendations(self) -> List[str]:
        """Generate high-level strategic recommendations"""

        recommendations = []

        # Analyze learning trends
        trends = self._analyze_learning_trends()
        if trends['trend_direction'] == 'declining':
            recommendations.append("Consider refreshing learning strategies - performance is declining")
        elif trends['trend_direction'] == 'stable' and trends['performance_variance'] > 0.1:
            recommendations.append("Reduce strategy variance to improve consistency")

        # Analyze strategy effectiveness
        effective_strategies = self._identify_effective_strategies()
        if effective_strategies['total_strategies_analyzed'] > 0:
            top_strategy = list(effective_strategies['top_strategies'].keys())[0]
            recommendations.append(f"Increase usage of '{top_strategy}' - consistently high performance")

        # Analyze failure modes
        failure_analysis = self._analyze_failure_modes()
        if failure_analysis['failure_rate'] > 0.3:
            recommendations.append("High failure rate detected - review failure modes and implement preventive measures")

        # Knowledge base recommendations
        if len(self.meta_knowledge_base) < 10:
            recommendations.append("Accumulate more diverse learning experiences to improve meta-knowledge")

        return recommendations[:5]  # Top 5 recommendations

    def save_persistent_data(self):
        """Save meta-learning data to persistent storage"""
        try:
            # Save episode history
            episodes_file = self.storage_path / "episodes.json"
            episodes_data = []
            for episode in self.episode_history[-100:]:  # Keep last 100 episodes
                episode_dict = {
                    'episode_id': episode.episode_id,
                    'task_type': episode.task_type,
                    'task_description': episode.task_description,
                    'agent_id': episode.agent_id,
                    'initial_performance': episode.initial_performance,
                    'final_performance': episode.final_performance,
                    'learning_duration': episode.learning_duration.total_seconds(),
                    'hyperparameters': episode.hyperparameters,
                    'strategies_used': episode.strategies_used,
                    'transfer_source': episode.transfer_source,
                    'success_metrics': episode.success_metrics,
                    'failure_points': episode.failure_points,
                    'meta_features': episode.meta_features,
                    'contextual_factors': episode.contextual_factors
                }
                episodes_data.append(episode_dict)

            with open(episodes_file, 'w') as f:
                json.dump(episodes_data, f, indent=2, default=str)

            # Save meta-knowledge base
            knowledge_file = self.storage_path / "meta_knowledge.json"
            knowledge_data = {}
            for knowledge_id, knowledge in self.meta_knowledge_base.items():
                knowledge_data[knowledge_id] = {
                    'knowledge_id': knowledge.knowledge_id,
                    'knowledge_type': knowledge.knowledge_type.value,
                    'pattern_description': knowledge.pattern_description,
                    'applicability_conditions': knowledge.applicability_conditions,
                    'effectiveness_score': knowledge.effectiveness_score,
                    'confidence_level': knowledge.confidence_level,
                    'usage_count': knowledge.usage_count,
                    'success_rate': knowledge.success_rate,
                    'discovery_episodes': knowledge.discovery_episodes,
                    'validation_episodes': knowledge.validation_episodes,
                    'last_updated': knowledge.last_updated.isoformat()
                }

            with open(knowledge_file, 'w') as f:
                json.dump(knowledge_data, f, indent=2)

            logger.info(f"Saved {len(episodes_data)} episodes and {len(knowledge_data)} knowledge items")

        except Exception as e:
            logger.error(f"Failed to save persistent data: {e}")

    def load_persistent_data(self):
        """Load meta-learning data from persistent storage"""
        try:
            # Load episode history
            episodes_file = self.storage_path / "episodes.json"
            if episodes_file.exists():
                with open(episodes_file, 'r') as f:
                    episodes_data = json.load(f)

                for episode_dict in episodes_data:
                    learning_curve = []
                    episode = LearningEpisode(
                        episode_id=episode_dict['episode_id'],
                        task_type=episode_dict['task_type'],
                        task_description=episode_dict['task_description'],
                        agent_id=episode_dict['agent_id'],
                        initial_performance=episode_dict['initial_performance'],
                        final_performance=episode_dict['final_performance'],
                        learning_duration=timedelta(seconds=episode_dict['learning_duration']),
                        hyperparameters=episode_dict['hyperparameters'],
                        learning_curve=learning_curve,
                        strategies_used=episode_dict['strategies_used'],
                        transfer_source=episode_dict.get('transfer_source'),
                        success_metrics=episode_dict.get('success_metrics', {}),
                        failure_points=episode_dict.get('failure_points', []),
                        meta_features=episode_dict.get('meta_features', {}),
                        contextual_factors=episode_dict.get('contextual_factors', {})
                    )
                    self.episode_history.append(episode)

            # Load meta-knowledge base
            knowledge_file = self.storage_path / "meta_knowledge.json"
            if knowledge_file.exists():
                with open(knowledge_file, 'r') as f:
                    knowledge_data = json.load(f)

                for knowledge_id, knowledge_dict in knowledge_data.items():
                    knowledge = MetaKnowledge(
                        knowledge_id=knowledge_dict['knowledge_id'],
                        knowledge_type=MetaKnowledgeType(knowledge_dict['knowledge_type']),
                        pattern_description=knowledge_dict['pattern_description'],
                        applicability_conditions=knowledge_dict['applicability_conditions'],
                        effectiveness_score=knowledge_dict['effectiveness_score'],
                        confidence_level=knowledge_dict['confidence_level'],
                        usage_count=knowledge_dict['usage_count'],
                        success_rate=knowledge_dict.get('success_rate', 0.0),
                        discovery_episodes=knowledge_dict.get('discovery_episodes', []),
                        validation_episodes=knowledge_dict.get('validation_episodes', []),
                        last_updated=datetime.fromisoformat(knowledge_dict['last_updated'])
                    )
                    self.meta_knowledge_base[knowledge_id] = knowledge

            logger.info(f"Loaded {len(self.episode_history)} episodes and {len(self.meta_knowledge_base)} knowledge items")

        except Exception as e:
            logger.error(f"Failed to load persistent data: {e}")


async def demonstrate_meta_learning():
    """Demonstrate the meta-learning optimization system"""

    orchestrator = MetaLearningOrchestrator()

    # Create sample learning episodes
    sample_episodes = [
        LearningEpisode(
            episode_id="ep_001",
            task_type="classification",
            task_description="Image classification task",
            agent_id="coder_agent_001",
            initial_performance=0.3,
            final_performance=0.85,
            learning_duration=timedelta(hours=2),
            hyperparameters={'learning_rate': 0.001, 'batch_size': 32},
            learning_curve=[(datetime.now(), 0.3), (datetime.now(), 0.6), (datetime.now(), 0.85)],
            strategies_used=['supervised_learning', 'data_augmentation'],
            success_metrics={'accuracy': 0.85, 'precision': 0.83},
            failure_points=[],
            contextual_factors={'dataset_size': 10000}
        ),
        LearningEpisode(
            episode_id="ep_002",
            task_type="regression",
            task_description="Price prediction task",
            agent_id="evaluator_agent_001",
            initial_performance=0.2,
            final_performance=0.75,
            learning_duration=timedelta(hours=1.5),
            hyperparameters={'learning_rate': 0.01, 'batch_size': 64},
            learning_curve=[(datetime.now(), 0.2), (datetime.now(), 0.5), (datetime.now(), 0.75)],
            strategies_used=['regression', 'feature_engineering'],
            success_metrics={'mse': 0.15, 'r2': 0.75},
            failure_points=['overfitting_detected'],
            contextual_factors={'feature_count': 20}
        )
    ]

    print("=== Meta-Learning Optimization System Demonstration ===\n")

    # Process learning episodes
    for episode in sample_episodes:
        print(f"Processing episode: {episode.episode_id}")
        result = await orchestrator.learn_from_episode(episode)
        print(f"  - Extracted {len(result['extracted_features'])} feature categories")
        print(f"  - Recognized {len(result['recognized_patterns'])} patterns")
        print(f"  - Applied {len(result['meta_knowledge_updates'])} knowledge updates")
        print()

    # Generate optimization strategy for a new task
    print("Generating optimization strategy for new classification task...")
    strategy = await orchestrator.optimize_learning_strategy(
        target_task_type="classification",
        agent_characteristics={'agent_type': 'coder_agent'},
        constraints={'max_training_time': 3600}
    )

    print(f"Strategy confidence: {strategy['confidence']:.2f}")
    print(f"Number of recommendations: {len(strategy['combined_recommendations'])}")
    print()

    # Evaluate performance of a completed episode
    print("Evaluating episode performance...")
    evaluation = await orchestrator.evaluate_learning_performance(sample_episodes[0])
    print(f"Relative performance: {evaluation['relative_performance']['relative_performance']}")
    print(f"Percentile rank: {evaluation['relative_performance']['percentile_rank']:.1f}")
    print(f"Improvement opportunities: {len(evaluation['improvement_opportunities'])}")
    print()

    # Get meta-insights
    print("Meta-learning insights:")
    insights = orchestrator.get_meta_insights()
    print(f"  - Total episodes analyzed: {insights['total_episodes_analyzed']}")
    print(f"  - Meta-knowledge items: {insights['meta_knowledge_count']}")
    print(f"  - Learning trend: {insights['learning_trends']['trend_direction']}")
    print(f"  - Strategic recommendations: {len(insights['strategic_recommendations'])}")

    for i, rec in enumerate(insights['strategic_recommendations'][:3], 1):
        print(f"    {i}. {rec}")

    print("\n=== Meta-Learning Optimization System Demonstration Complete ===")


if __name__ == "__main__":
    asyncio.run(demonstrate_meta_learning())