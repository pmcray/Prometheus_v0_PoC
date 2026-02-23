"""
Symbolic Math Agent (v0.71)

Provides formal mathematical reasoning capabilities through SymPy integration.
This bridges the gap between neural (LLM) reasoning and formal symbolic computation.

The SymbolicMathAgent is a specialized tool that evolved agents can call
to perform rigorous mathematical operations.
"""

import logging
from typing import Optional, Dict, Any, List, Union, Tuple
from dataclasses import dataclass
import re

try:
    import sympy as sp
    from sympy.parsing.sympy_parser import parse_expr
    from sympy import Symbol, sympify, simplify, solve, diff, integrate
    from sympy import Matrix, latex, pretty
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    logging.warning("SymPy not installed. Install with: pip install sympy")


@dataclass
class MathResult:
    """Result from a symbolic math operation."""
    success: bool
    result: Optional[Any] = None
    latex_repr: Optional[str] = None
    pretty_repr: Optional[str] = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SymbolicMathAgent:
    """
    Formal mathematics agent using SymPy.

    Capabilities:
    - Algebraic equation solving
    - Symbolic differentiation and integration
    - Matrix operations
    - Expression simplification
    - Theorem proving (basic)
    - LaTeX generation

    This is a TOOL agent - it doesn't evolve, but provides a reliable
    formal reasoning capability that evolved agents can learn to use.
    """

    def __init__(self):
        """Initialize the symbolic math agent."""
        if not SYMPY_AVAILABLE:
            raise ImportError("SymPy is required. Install: pip install sympy")

        self.stats = {
            "operations": 0,
            "solutions": 0,
            "derivatives": 0,
            "integrals": 0,
            "simplifications": 0,
            "errors": 0
        }

        logging.info("SymbolicMathAgent initialized with SymPy")

    def parse_expression(self, expr_str: str) -> MathResult:
        """
        Parse a string into a SymPy expression.

        Args:
            expr_str: Mathematical expression as string (e.g., "x**2 + 2*x + 1")

        Returns:
            MathResult with parsed expression
        """
        try:
            expr = parse_expr(expr_str)
            return MathResult(
                success=True,
                result=expr,
                latex_repr=latex(expr),
                pretty_repr=pretty(expr),
                metadata={"input": expr_str, "type": str(type(expr))}
            )
        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Expression parsing failed: {e}")
            return MathResult(
                success=False,
                error=str(e),
                metadata={"input": expr_str}
            )

    def solve_equation(
        self,
        equation_str: str,
        variable: str = "x"
    ) -> MathResult:
        """
        Solve an algebraic equation.

        Args:
            equation_str: Equation as string (e.g., "x**2 - 4")
            variable: Variable to solve for

        Returns:
            MathResult with solutions
        """
        logging.info(f"Solving: {equation_str} for {variable}")

        try:
            # Parse equation
            expr = parse_expr(equation_str)
            var = Symbol(variable)

            # Solve
            raw_solutions = solve(expr, var)

            # Convert solutions to list if needed
            if isinstance(raw_solutions, dict):
                # Handle dict case (system of equations)
                solutions = [raw_solutions[var]] if var in raw_solutions else list(raw_solutions.values())
            elif isinstance(raw_solutions, list):
                solutions = raw_solutions
            else:
                solutions = [raw_solutions]

            self.stats["operations"] += 1
            self.stats["solutions"] += 1

            return MathResult(
                success=True,
                result=solutions,
                latex_repr=str([latex(s) for s in solutions]),
                pretty_repr=str([pretty(s) for s in solutions]),
                metadata={
                    "equation": equation_str,
                    "variable": variable,
                    "num_solutions": len(solutions)
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Equation solving failed: {e}")
            return MathResult(
                success=False,
                error=str(e),
                metadata={"equation": equation_str, "variable": variable}
            )

    def differentiate(
        self,
        expr_str: str,
        variable: str = "x",
        order: int = 1
    ) -> MathResult:
        """
        Compute symbolic derivative.

        Args:
            expr_str: Expression to differentiate
            variable: Variable to differentiate with respect to
            order: Order of derivative (1 for first derivative, etc.)

        Returns:
            MathResult with derivative
        """
        logging.info(f"Differentiating: {expr_str} w.r.t. {variable} (order {order})")

        try:
            expr = parse_expr(expr_str)
            var = Symbol(variable)

            # Compute derivative
            derivative = diff(expr, var, order)

            self.stats["operations"] += 1
            self.stats["derivatives"] += 1

            return MathResult(
                success=True,
                result=derivative,
                latex_repr=latex(derivative),
                pretty_repr=pretty(derivative),
                metadata={
                    "expression": expr_str,
                    "variable": variable,
                    "order": order
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Differentiation failed: {e}")
            return MathResult(
                success=False,
                error=str(e),
                metadata={"expression": expr_str, "variable": variable}
            )

    def integrate(
        self,
        expr_str: str,
        variable: str = "x",
        limits: Optional[Tuple[float, float]] = None
    ) -> MathResult:
        """
        Compute symbolic integral.

        Args:
            expr_str: Expression to integrate
            variable: Variable to integrate with respect to
            limits: Optional (lower, upper) bounds for definite integral

        Returns:
            MathResult with integral
        """
        logging.info(f"Integrating: {expr_str} w.r.t. {variable}")

        try:
            expr = parse_expr(expr_str)
            var = Symbol(variable)

            # Compute integral
            if limits:
                result = integrate(expr, (var, limits[0], limits[1]))
            else:
                result = integrate(expr, var)

            self.stats["operations"] += 1
            self.stats["integrals"] += 1

            return MathResult(
                success=True,
                result=result,
                latex_repr=latex(result),
                pretty_repr=pretty(result),
                metadata={
                    "expression": expr_str,
                    "variable": variable,
                    "limits": limits,
                    "definite": limits is not None
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Integration failed: {e}")
            return MathResult(
                success=False,
                error=str(e),
                metadata={"expression": expr_str, "variable": variable}
            )

    def simplify_expression(self, expr_str: str) -> MathResult:
        """
        Simplify a mathematical expression.

        Args:
            expr_str: Expression to simplify

        Returns:
            MathResult with simplified expression
        """
        logging.info(f"Simplifying: {expr_str}")

        try:
            expr = parse_expr(expr_str)
            simplified = simplify(expr)

            self.stats["operations"] += 1
            self.stats["simplifications"] += 1

            return MathResult(
                success=True,
                result=simplified,
                latex_repr=latex(simplified),
                pretty_repr=pretty(simplified),
                metadata={
                    "original": expr_str,
                    "original_complexity": len(str(expr)),
                    "simplified_complexity": len(str(simplified))
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Simplification failed: {e}")
            return MathResult(
                success=False,
                error=str(e),
                metadata={"expression": expr_str}
            )

    def solve_system(
        self,
        equations: List[str],
        variables: List[str]
    ) -> MathResult:
        """
        Solve a system of equations.

        Args:
            equations: List of equation strings
            variables: List of variable names to solve for

        Returns:
            MathResult with solution dictionary
        """
        logging.info(f"Solving system: {len(equations)} equations, {len(variables)} variables")

        try:
            # Parse equations and variables
            exprs = [parse_expr(eq) for eq in equations]
            vars = [Symbol(v) for v in variables]

            # Solve system
            solutions = solve(exprs, vars)

            self.stats["operations"] += 1
            self.stats["solutions"] += 1

            return MathResult(
                success=True,
                result=solutions,
                latex_repr=latex(solutions),
                pretty_repr=pretty(solutions),
                metadata={
                    "num_equations": len(equations),
                    "num_variables": len(variables),
                    "equations": equations,
                    "variables": variables
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"System solving failed: {e}")
            return MathResult(
                success=False,
                error=str(e),
                metadata={"equations": equations, "variables": variables}
            )

    def matrix_operation(
        self,
        operation: str,
        matrices: List[List[List[float]]]
    ) -> MathResult:
        """
        Perform matrix operations.

        Args:
            operation: "multiply", "inverse", "determinant", "eigenvalues"
            matrices: List of matrices (each matrix is a list of rows)

        Returns:
            MathResult with operation result
        """
        logging.info(f"Matrix operation: {operation}")

        try:
            # Convert to SymPy matrices
            sp_matrices = [Matrix(m) for m in matrices]

            result = None
            if operation == "multiply" and len(sp_matrices) >= 2:
                result = sp_matrices[0] * sp_matrices[1]
            elif operation == "inverse" and len(sp_matrices) >= 1:
                result = sp_matrices[0].inv()
            elif operation == "determinant" and len(sp_matrices) >= 1:
                result = sp_matrices[0].det()
            elif operation == "eigenvalues" and len(sp_matrices) >= 1:
                result = sp_matrices[0].eigenvals()
            else:
                raise ValueError(f"Unknown operation or wrong number of matrices: {operation}")

            self.stats["operations"] += 1

            return MathResult(
                success=True,
                result=result,
                latex_repr=latex(result),
                pretty_repr=pretty(result),
                metadata={
                    "operation": operation,
                    "num_matrices": len(matrices)
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Matrix operation failed: {e}")
            return MathResult(
                success=False,
                error=str(e),
                metadata={"operation": operation}
            )

    def verify_identity(
        self,
        expr1_str: str,
        expr2_str: str
    ) -> MathResult:
        """
        Verify if two expressions are mathematically equivalent.

        Args:
            expr1_str: First expression
            expr2_str: Second expression

        Returns:
            MathResult with True/False result
        """
        logging.info(f"Verifying: {expr1_str} == {expr2_str}")

        try:
            expr1 = parse_expr(expr1_str)
            expr2 = parse_expr(expr2_str)

            # Simplify difference
            diff = simplify(expr1 - expr2)
            equivalent = diff == 0

            self.stats["operations"] += 1

            return MathResult(
                success=True,
                result=equivalent,
                metadata={
                    "expr1": expr1_str,
                    "expr2": expr2_str,
                    "equivalent": equivalent,
                    "difference": str(diff)
                }
            )

        except Exception as e:
            self.stats["errors"] += 1
            logging.error(f"Identity verification failed: {e}")
            return MathResult(
                success=False,
                error=str(e),
                metadata={"expr1": expr1_str, "expr2": expr2_str}
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            **self.stats,
            "sympy_available": SYMPY_AVAILABLE,
            "success_rate": (
                (self.stats["operations"] - self.stats["errors"]) /
                max(self.stats["operations"], 1)
            )
        }


def get_symbolic_math_agent() -> SymbolicMathAgent:
    """Factory function to create symbolic math agent."""
    return SymbolicMathAgent()


# Convenience functions for agent use
def solve(equation: str, variable: str = "x") -> Any:
    """Solve equation and return solutions."""
    agent = get_symbolic_math_agent()
    result = agent.solve_equation(equation, variable)
    return result.result if result.success else None


def differentiate(expr: str, variable: str = "x", order: int = 1) -> Any:
    """Differentiate expression and return derivative."""
    agent = get_symbolic_math_agent()
    result = agent.differentiate(expr, variable, order)
    return result.result if result.success else None


def integrate_expr(expr: str, variable: str = "x", limits: Optional[Tuple[float, float]] = None) -> Any:
    """Integrate expression and return result."""
    agent = get_symbolic_math_agent()
    result = agent.integrate(expr, variable, limits)
    return result.result if result.success else None


def simplify_expr(expr: str) -> Any:
    """Simplify expression and return result."""
    agent = get_symbolic_math_agent()
    result = agent.simplify_expression(expr)
    return result.result if result.success else None
