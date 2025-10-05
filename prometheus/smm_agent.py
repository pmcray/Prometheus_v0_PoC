"""
Self-Modification Module (SMM) Agent v0.1
Core agent responsible for proposing and implementing safe self-modifications

This agent generates targeted code improvements, creates patches, and coordinates
with the IEE system to ensure only beneficial modifications are accepted.
"""

import os
import ast
import git
import json
import time
import logging
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import hashlib

from .iee import IEEHarness, PatchVerificationResult
from .fitness_monitor import FitnessMonotonicityMonitor
from .reward_hacking_detector import RewardHackingDetector

@dataclass
class ModificationProposal:
    """Represents a proposed self-modification"""
    proposal_id: str
    modification_type: str  # 'optimization', 'bug_fix', 'feature_addition', 'refactoring'
    target_files: List[str]
    description: str
    rationale: str
    expected_benefits: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    patch_content: str
    confidence_score: float  # 0.0 to 1.0
    creation_timestamp: str
    estimated_impact: str  # 'low', 'medium', 'high'

@dataclass
class ModificationResult:
    """Result of applying a self-modification"""
    proposal_id: str
    modification_applied: bool
    verification_result: Optional[PatchVerificationResult]
    actual_benefits: Dict[str, Any]
    lessons_learned: Dict[str, Any]
    application_timestamp: str

class SelfModificationAgent:
    """
    Self-Modification Module (SMM) Agent v0.1

    Core responsibilities:
    1. Analyze current system performance and identify improvement opportunities
    2. Generate targeted modification proposals
    3. Create git patches for proposed changes
    4. Coordinate with IEE system for safe verification
    5. Learn from modification outcomes to improve future proposals
    """

    def __init__(self,
                 codebase_path: str = ".",
                 iee_harness: Optional[IEEHarness] = None,
                 max_concurrent_proposals: int = 3):

        self.codebase_path = Path(codebase_path).resolve()
        self.max_concurrent_proposals = max_concurrent_proposals

        # Initialize IEE integration
        self.iee_harness = iee_harness or IEEHarness(
            base_codebase_path=str(self.codebase_path)
        )

        # Track proposals and results
        self.active_proposals: Dict[str, ModificationProposal] = {}
        self.proposal_history: List[ModificationProposal] = []
        self.modification_results: List[ModificationResult] = []

        # Learning and adaptation
        self.success_patterns: Dict[str, float] = {}
        self.failure_patterns: Dict[str, float] = {}
        self.performance_trends: List[Dict[str, Any]] = []

        # Initialize git repository
        try:
            self.repo = git.Repo(self.codebase_path)
        except git.InvalidGitRepositoryError:
            self.repo = git.Repo.init(self.codebase_path)

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.logger.info("🤖 SMM Agent v0.1 initialized")

    def analyze_improvement_opportunities(self) -> List[Dict[str, Any]]:
        """
        Analyze the codebase to identify potential improvement opportunities

        Returns:
            List of improvement opportunities with analysis
        """
        self.logger.info("🔍 Analyzing improvement opportunities")

        opportunities = []

        # 1. Performance bottleneck analysis
        performance_opportunities = self._analyze_performance_bottlenecks()
        opportunities.extend(performance_opportunities)

        # 2. Code quality improvements
        quality_opportunities = self._analyze_code_quality_issues()
        opportunities.extend(quality_opportunities)

        # 3. Test coverage gaps
        test_opportunities = self._analyze_test_coverage_gaps()
        opportunities.extend(test_opportunities)

        # 4. Dependency optimization
        dependency_opportunities = self._analyze_dependency_optimization()
        opportunities.extend(dependency_opportunities)

        # 5. Architecture improvements
        architecture_opportunities = self._analyze_architecture_improvements()
        opportunities.extend(architecture_opportunities)

        # Rank opportunities by impact and feasibility
        ranked_opportunities = self._rank_opportunities(opportunities)

        self.logger.info(f"📊 Found {len(ranked_opportunities)} improvement opportunities")
        return ranked_opportunities

    def generate_modification_proposal(self, opportunity: Dict[str, Any]) -> ModificationProposal:
        """
        Generate a specific modification proposal from an improvement opportunity

        Args:
            opportunity: Improvement opportunity analysis

        Returns:
            Detailed modification proposal
        """
        self.logger.info(f"💡 Generating modification proposal for: {opportunity['type']}")

        # Generate unique proposal ID
        proposal_id = self._generate_proposal_id(opportunity)

        # Create the actual code modification
        patch_content, target_files = self._create_modification_patch(opportunity)

        # Assess risk and expected benefits
        risk_assessment = self._assess_modification_risk(opportunity, patch_content)
        expected_benefits = self._estimate_expected_benefits(opportunity)

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(opportunity, risk_assessment)

        proposal = ModificationProposal(
            proposal_id=proposal_id,
            modification_type=opportunity['type'],
            target_files=target_files,
            description=opportunity['description'],
            rationale=opportunity['rationale'],
            expected_benefits=expected_benefits,
            risk_assessment=risk_assessment,
            patch_content=patch_content,
            confidence_score=confidence_score,
            creation_timestamp=datetime.now().isoformat(),
            estimated_impact=opportunity.get('impact', 'medium')
        )

        # Store proposal
        self.active_proposals[proposal_id] = proposal
        self.proposal_history.append(proposal)

        self.logger.info(f"✅ Generated proposal {proposal_id} with confidence {confidence_score:.2f}")
        return proposal

    def apply_modification(self, proposal: ModificationProposal) -> ModificationResult:
        """
        Apply a modification proposal using the IEE verification system

        Args:
            proposal: The modification proposal to apply

        Returns:
            Result of the modification attempt
        """
        self.logger.info(f"🚀 Applying modification proposal {proposal.proposal_id}")

        start_time = time.time()

        try:
            # Use IEE harness to safely verify and apply the modification
            verification_result = self.iee_harness.verify_patch(
                patch_content=proposal.patch_content,
                patch_description=f"{proposal.modification_type}: {proposal.description}"
            )

            modification_applied = verification_result.verification_passed

            if modification_applied:
                # Apply patch to the actual codebase
                self._apply_patch_to_codebase(proposal.patch_content)
                self.logger.info(f"✅ Successfully applied modification {proposal.proposal_id}")
            else:
                self.logger.warning(f"❌ Modification {proposal.proposal_id} rejected by IEE")

            # Calculate actual benefits
            actual_benefits = self._calculate_actual_benefits(verification_result)

            # Learn from the outcome
            lessons_learned = self._extract_lessons_learned(proposal, verification_result)

            result = ModificationResult(
                proposal_id=proposal.proposal_id,
                modification_applied=modification_applied,
                verification_result=verification_result,
                actual_benefits=actual_benefits,
                lessons_learned=lessons_learned,
                application_timestamp=datetime.now().isoformat()
            )

            # Store result and update learning
            self.modification_results.append(result)
            self._update_learning_patterns(proposal, result)

            # Clean up active proposal
            if proposal.proposal_id in self.active_proposals:
                del self.active_proposals[proposal.proposal_id]

            return result

        except Exception as e:
            self.logger.error(f"❌ Failed to apply modification {proposal.proposal_id}: {str(e)}")

            error_result = ModificationResult(
                proposal_id=proposal.proposal_id,
                modification_applied=False,
                verification_result=None,
                actual_benefits={},
                lessons_learned={"error": str(e), "failure_type": "application_error"},
                application_timestamp=datetime.now().isoformat()
            )

            self.modification_results.append(error_result)
            return error_result

    def _analyze_performance_bottlenecks(self) -> List[Dict[str, Any]]:
        """Analyze code for performance bottlenecks"""
        opportunities = []

        # Simple heuristic analysis - could be enhanced with profiling data
        for py_file in self.codebase_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()

                tree = ast.parse(content)

                # Look for nested loops (potential O(n^2) issues)
                nested_loop_count = self._count_nested_loops(tree)
                if nested_loop_count > 2:
                    opportunities.append({
                        "type": "optimization",
                        "description": f"Reduce nested loop complexity in {py_file.name}",
                        "rationale": f"Found {nested_loop_count} nested loops which may cause performance issues",
                        "file": str(py_file),
                        "impact": "high",
                        "feasibility": 0.7
                    })

                # Look for inefficient string operations
                string_concat_count = self._count_string_concatenations(tree)
                if string_concat_count > 10:
                    opportunities.append({
                        "type": "optimization",
                        "description": f"Optimize string operations in {py_file.name}",
                        "rationale": f"Found {string_concat_count} string concatenations, consider using join()",
                        "file": str(py_file),
                        "impact": "medium",
                        "feasibility": 0.9
                    })

            except (SyntaxError, UnicodeDecodeError):
                continue

        return opportunities

    def _analyze_code_quality_issues(self) -> List[Dict[str, Any]]:
        """Analyze code for quality improvements"""
        opportunities = []

        for py_file in self.codebase_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')

                # Check for long functions
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_length = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 50
                        if func_length > 50:  # Long function threshold
                            opportunities.append({
                                "type": "refactoring",
                                "description": f"Refactor long function '{node.name}' in {py_file.name}",
                                "rationale": f"Function is {func_length} lines long, consider breaking into smaller functions",
                                "file": str(py_file),
                                "function": node.name,
                                "impact": "medium",
                                "feasibility": 0.8
                            })

                # Check for missing docstrings
                missing_docstrings = self._find_missing_docstrings(tree)
                if missing_docstrings:
                    opportunities.append({
                        "type": "documentation",
                        "description": f"Add missing docstrings in {py_file.name}",
                        "rationale": f"Found {len(missing_docstrings)} functions/classes without docstrings",
                        "file": str(py_file),
                        "missing_items": missing_docstrings,
                        "impact": "low",
                        "feasibility": 1.0
                    })

            except (SyntaxError, UnicodeDecodeError):
                continue

        return opportunities

    def _analyze_test_coverage_gaps(self) -> List[Dict[str, Any]]:
        """Analyze test coverage and identify gaps"""
        opportunities = []

        # Find all Python modules
        python_files = list(self.codebase_path.rglob("*.py"))
        test_files = [f for f in python_files if "test" in f.name.lower()]
        source_files = [f for f in python_files if "test" not in f.name.lower() and not f.name.startswith("__")]

        # Simple heuristic: if source file has no corresponding test file
        for source_file in source_files:
            test_file_exists = any(
                source_file.stem in test_file.name for test_file in test_files
            )

            if not test_file_exists and source_file.stat().st_size > 1000:  # Only for non-trivial files
                opportunities.append({
                    "type": "testing",
                    "description": f"Create tests for {source_file.name}",
                    "rationale": f"No test file found for {source_file.name}",
                    "file": str(source_file),
                    "impact": "medium",
                    "feasibility": 0.6
                })

        return opportunities

    def _analyze_dependency_optimization(self) -> List[Dict[str, Any]]:
        """Analyze dependencies for optimization opportunities"""
        opportunities = []

        # Check requirements.txt for unused dependencies
        requirements_file = self.codebase_path / "requirements.txt"
        if requirements_file.exists():
            with open(requirements_file, 'r') as f:
                requirements = f.read()

            # Simple check - could be enhanced with actual import analysis
            if len(requirements.split('\n')) > 20:  # Many dependencies
                opportunities.append({
                    "type": "optimization",
                    "description": "Audit and optimize dependencies",
                    "rationale": "Large number of dependencies may impact startup time",
                    "file": str(requirements_file),
                    "impact": "medium",
                    "feasibility": 0.5
                })

        return opportunities

    def _analyze_architecture_improvements(self) -> List[Dict[str, Any]]:
        """Analyze architecture for improvement opportunities"""
        opportunities = []

        # Look for circular imports (simplified check)
        import_graph = self._build_import_graph()
        if self._has_circular_dependencies(import_graph):
            opportunities.append({
                "type": "refactoring",
                "description": "Resolve circular import dependencies",
                "rationale": "Circular imports can cause import errors and design issues",
                "impact": "high",
                "feasibility": 0.4
            })

        return opportunities

    def _create_modification_patch(self, opportunity: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Create a git patch for the modification"""
        modification_type = opportunity['type']
        target_file = opportunity.get('file')

        if modification_type == "optimization" and "string operations" in opportunity['description']:
            return self._create_string_optimization_patch(target_file)
        elif modification_type == "documentation" and "docstrings" in opportunity['description']:
            return self._create_docstring_patch(target_file, opportunity.get('missing_items', []))
        elif modification_type == "refactoring" and "long function" in opportunity['description']:
            return self._create_function_refactoring_patch(target_file, opportunity.get('function'))
        else:
            # Generic improvement patch
            return self._create_generic_improvement_patch(opportunity)

    def _create_string_optimization_patch(self, file_path: str) -> Tuple[str, List[str]]:
        """Create a patch to optimize string operations"""
        # This is a simplified example - real implementation would be more sophisticated
        patch_content = f"""--- a/{file_path}
+++ b/{file_path}
@@ -1,3 +1,3 @@
 # String optimization patch
-result = ""
-for item in items:
-    result += str(item) + ", "
+# Optimized string concatenation
+result = ", ".join(str(item) for item in items)
"""
        return patch_content, [file_path]

    def _create_docstring_patch(self, file_path: str, missing_items: List[str]) -> Tuple[str, List[str]]:
        """Create a patch to add missing docstrings"""
        # Simplified docstring addition patch
        patch_content = f"""--- a/{file_path}
+++ b/{file_path}
@@ -10,6 +10,9 @@
 def example_function():
+    \"\"\"
+    Example function with added documentation.
+    \"\"\"
     pass
"""
        return patch_content, [file_path]

    def _create_function_refactoring_patch(self, file_path: str, function_name: str) -> Tuple[str, List[str]]:
        """Create a patch to refactor a long function"""
        # Simplified function refactoring patch
        patch_content = f"""--- a/{file_path}
+++ b/{file_path}
@@ -20,10 +20,15 @@
-def {function_name}():
+def {function_name}():
+    \"\"\"Refactored {function_name} into smaller components\"\"\"
+    _helper_function_1()
+    _helper_function_2()
+
+def _helper_function_1():
+    \"\"\"Helper function extracted from {function_name}\"\"\"
     pass
+
+def _helper_function_2():
+    \"\"\"Helper function extracted from {function_name}\"\"\"
+    pass
"""
        return patch_content, [file_path]

    def _create_generic_improvement_patch(self, opportunity: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Create a generic improvement patch"""
        # Placeholder for generic improvements
        file_path = opportunity.get('file', 'generic.py')
        patch_content = f"""--- a/{file_path}
+++ b/{file_path}
@@ -1,3 +1,6 @@
+# Generic improvement patch
+# Type: {opportunity['type']}
+# Description: {opportunity['description']}
 # Original code
 pass
"""
        return patch_content, [file_path]

    def _apply_patch_to_codebase(self, patch_content: str):
        """Apply the verified patch to the actual codebase"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch_content)
            patch_file = f.name

        try:
            # Apply patch using git
            result = subprocess.run(
                ['git', 'apply', patch_file],
                cwd=self.codebase_path,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Commit the changes
                self.repo.index.add(['.'])
                self.repo.index.commit("SMM: Applied verified self-modification")
                self.logger.info("✅ Patch applied and committed to codebase")
            else:
                raise RuntimeError(f"Git apply failed: {result.stderr}")

        finally:
            os.unlink(patch_file)

    # Helper methods for analysis
    def _count_nested_loops(self, tree: ast.AST) -> int:
        """Count nested loops in AST"""
        max_depth = 0

        class LoopCounter(ast.NodeVisitor):
            def __init__(self):
                self.current_depth = 0
                self.max_depth = 0

            def visit_For(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1

            def visit_While(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1

        counter = LoopCounter()
        counter.visit(tree)
        return counter.max_depth

    def _count_string_concatenations(self, tree: ast.AST) -> int:
        """Count string concatenations in AST"""
        count = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                count += 1

        return count

    def _find_missing_docstrings(self, tree: ast.AST) -> List[str]:
        """Find functions and classes missing docstrings"""
        missing = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    missing.append(node.name)

        return missing

    def _build_import_graph(self) -> Dict[str, Set[str]]:
        """Build import dependency graph"""
        import_graph = {}

        for py_file in self.codebase_path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    tree = ast.parse(f.read())

                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module)

                import_graph[str(py_file)] = imports

            except (SyntaxError, UnicodeDecodeError):
                continue

        return import_graph

    def _has_circular_dependencies(self, import_graph: Dict[str, Set[str]]) -> bool:
        """Check for circular dependencies (simplified)"""
        # Simplified circular dependency check
        for file, imports in import_graph.items():
            for imported in imports:
                if imported in import_graph and file in import_graph[imported]:
                    return True
        return False

    def _rank_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank opportunities by impact and feasibility"""
        impact_scores = {"high": 3, "medium": 2, "low": 1}

        for opp in opportunities:
            impact_score = impact_scores.get(opp.get('impact', 'medium'), 2)
            feasibility_score = opp.get('feasibility', 0.5)
            opp['priority_score'] = impact_score * feasibility_score

        return sorted(opportunities, key=lambda x: x['priority_score'], reverse=True)

    def _generate_proposal_id(self, opportunity: Dict[str, Any]) -> str:
        """Generate unique proposal ID"""
        content = f"{opportunity['type']}{opportunity['description']}{time.time()}"
        return f"smm_{hashlib.md5(content.encode()).hexdigest()[:8]}"

    def _assess_modification_risk(self, opportunity: Dict[str, Any], patch_content: str) -> Dict[str, Any]:
        """Assess risk of applying modification"""
        risk_factors = {
            "code_complexity": 0.3,
            "test_coverage": 0.2,
            "critical_component": 0.4 if "agent" in opportunity.get('file', '') else 0.1,
            "patch_size": min(1.0, len(patch_content.split('\n')) / 100)
        }

        total_risk = sum(risk_factors.values()) / len(risk_factors)

        return {
            "overall_risk": total_risk,
            "risk_factors": risk_factors,
            "risk_level": "high" if total_risk > 0.7 else "medium" if total_risk > 0.4 else "low"
        }

    def _estimate_expected_benefits(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate expected benefits from modification"""
        benefit_types = {
            "optimization": {"performance_improvement": 0.2, "resource_efficiency": 0.15},
            "refactoring": {"maintainability": 0.3, "code_quality": 0.25},
            "documentation": {"code_readability": 0.4, "developer_productivity": 0.1},
            "testing": {"reliability": 0.35, "bug_detection": 0.2}
        }

        mod_type = opportunity.get('type', 'optimization')
        return benefit_types.get(mod_type, {"general_improvement": 0.1})

    def _calculate_confidence_score(self, opportunity: Dict[str, Any], risk_assessment: Dict[str, Any]) -> float:
        """Calculate confidence score for the proposal"""
        feasibility = opportunity.get('feasibility', 0.5)
        risk_level = risk_assessment['overall_risk']

        # Higher feasibility and lower risk = higher confidence
        confidence = feasibility * (1 - risk_level)
        return max(0.1, min(1.0, confidence))

    def _calculate_actual_benefits(self, verification_result: PatchVerificationResult) -> Dict[str, Any]:
        """Calculate actual benefits from verification results"""
        if not verification_result.verification_passed:
            return {"no_benefits": "modification_rejected"}

        benchmark_results = verification_result.benchmark_results
        summary_metrics = benchmark_results.get("summary_metrics", {})

        return {
            "performance_change": summary_metrics.get("success_rate", 0.0),
            "execution_time_change": summary_metrics.get("average_execution_time_ms", 0.0),
            "verification_passed": True
        }

    def _extract_lessons_learned(self, proposal: ModificationProposal, verification_result: PatchVerificationResult) -> Dict[str, Any]:
        """Extract lessons learned from modification attempt"""
        lessons = {
            "proposal_type": proposal.modification_type,
            "success": verification_result.verification_passed if verification_result else False,
            "confidence_accuracy": None,
            "risk_assessment_accuracy": None
        }

        if verification_result:
            # Compare expected vs actual outcomes
            fitness_analysis = verification_result.benchmark_results.get("fitness_analysis", {})
            lessons["fitness_maintained"] = fitness_analysis.get("monotonicity_maintained", False)

            security_analysis = verification_result.benchmark_results.get("security_analysis", {})
            lessons["security_issues"] = security_analysis.get("reward_hacking_detected", False)

        return lessons

    def _update_learning_patterns(self, proposal: ModificationProposal, result: ModificationResult):
        """Update learning patterns based on modification outcome"""
        pattern_key = f"{proposal.modification_type}_{proposal.estimated_impact}"

        if result.modification_applied:
            # Success pattern
            self.success_patterns[pattern_key] = self.success_patterns.get(pattern_key, 0.5) + 0.1
            self.success_patterns[pattern_key] = min(1.0, self.success_patterns[pattern_key])
        else:
            # Failure pattern
            self.failure_patterns[pattern_key] = self.failure_patterns.get(pattern_key, 0.5) + 0.1
            self.failure_patterns[pattern_key] = min(1.0, self.failure_patterns[pattern_key])

    def generate_self_modification_report(self) -> Dict[str, Any]:
        """Generate comprehensive self-modification report"""
        total_proposals = len(self.proposal_history)
        successful_modifications = len([r for r in self.modification_results if r.modification_applied])

        return {
            "report_timestamp": datetime.now().isoformat(),
            "modification_statistics": {
                "total_proposals": total_proposals,
                "successful_modifications": successful_modifications,
                "success_rate": successful_modifications / total_proposals if total_proposals > 0 else 0,
                "active_proposals": len(self.active_proposals)
            },
            "learning_patterns": {
                "success_patterns": dict(self.success_patterns),
                "failure_patterns": dict(self.failure_patterns)
            },
            "modification_types": self._analyze_modification_types(),
            "performance_trends": self.performance_trends,
            "recommendations": self._generate_improvement_recommendations()
        }

    def _analyze_modification_types(self) -> Dict[str, Dict[str, Any]]:
        """Analyze modification types and their success rates"""
        type_analysis = {}

        for result in self.modification_results:
            proposal = next(
                (p for p in self.proposal_history if p.proposal_id == result.proposal_id),
                None
            )
            if proposal:
                mod_type = proposal.modification_type
                if mod_type not in type_analysis:
                    type_analysis[mod_type] = {"total": 0, "successful": 0}

                type_analysis[mod_type]["total"] += 1
                if result.modification_applied:
                    type_analysis[mod_type]["successful"] += 1

        # Calculate success rates
        for mod_type, stats in type_analysis.items():
            stats["success_rate"] = stats["successful"] / stats["total"] if stats["total"] > 0 else 0

        return type_analysis

    def _generate_improvement_recommendations(self) -> List[str]:
        """Generate recommendations for improving self-modification capability"""
        recommendations = []

        if len(self.modification_results) < 5:
            recommendations.append("Accumulate more modification attempts to improve learning")

        success_rate = len([r for r in self.modification_results if r.modification_applied]) / len(self.modification_results) if self.modification_results else 0

        if success_rate < 0.3:
            recommendations.append("Low success rate - consider more conservative modification proposals")
        elif success_rate > 0.8:
            recommendations.append("High success rate - consider more ambitious modifications")

        # Analyze failure patterns
        common_failures = max(self.failure_patterns.items(), key=lambda x: x[1], default=(None, 0))
        if common_failures[0] and common_failures[1] > 0.7:
            recommendations.append(f"Avoid {common_failures[0]} modifications - high failure rate")

        if not recommendations:
            recommendations.append("Self-modification capability is functioning well")

        return recommendations