#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARC Program Representation (v0.95)

This module defines the ARCProgram class for representing parametric
transformation programs for ARC-AGI tasks.

Key Concepts:
- Program = sequence of (operation, parameters) tuples
- Operations can have parameters (e.g., rotate(90), scale(2))
- Programs can be executed on grids to produce outputs
- Programs can be serialized/deserialized for storage

Example:
    program = ARCProgram([
        ('rotate', {'angle': 90}),
        ('filter_color', {'color': 2}),
        ('border', {'thickness': 1, 'color': 0})
    ])
    
    output = program.execute(input_grid)
"""

import numpy as np
from typing import List, Tuple, Dict, Any
import json
import copy


class ARCProgram:
    """
    Represents a parametric transformation program for ARC-AGI.
    
    A program consists of a sequence of operations, each with parameters.
    Programs can be executed on grids and serialized for storage.
    """
    
    def __init__(self, operations: List[Tuple[str, Dict[str, Any]]] = None):
        """
        Initialize program with operations.
        
        Args:
            operations: List of (operation_name, parameters) tuples
                       Example: [('rotate', {'angle': 90}), ...]
        """
        self.operations = operations if operations is not None else []
    
    def add_operation(self, op_name: str, params: Dict[str, Any] = None):
        """Add an operation to the program"""
        if params is None:
            params = {}
        self.operations.append((op_name, params))
    
    def copy(self) -> 'ARCProgram':
        """Create a deep copy of this program"""
        return ARCProgram(copy.deepcopy(self.operations))
    
    def execute(self, grid: np.ndarray, 
                operation_map: Dict[str, callable]) -> np.ndarray:
        """
        Execute program on input grid.
        
        Args:
            grid: Input grid (numpy array)
            operation_map: Dict mapping operation names to functions
        
        Returns:
            Transformed grid
        """
        result = grid.copy()
        
        for op_name, params in self.operations:
            if op_name not in operation_map:
                raise ValueError(f"Unknown operation: {op_name}")
            
            op_func = operation_map[op_name]
            
            try:
                result = op_func(result, **params)
            except Exception as e:
                # Operation failed, return current result
                # (allows partial program execution)
                print(f"  [Warning] Operation {op_name} failed: {e}")
                return result
        
        return result
    
    def to_pattern(self) -> List[str]:
        """
        Convert to v0.94-style pattern (for compatibility).
        
        Returns:
            List of strings like ['rotate(angle=90)', 'filter_color(color=2)']
        """
        pattern = []
        for op_name, params in self.operations:
            if params:
                param_str = ','.join([f"{k}={v}" for k, v in sorted(params.items())])
                pattern.append(f"{op_name}({param_str})")
            else:
                pattern.append(op_name)
        return pattern
    
    @staticmethod
    def from_pattern(pattern: List[str]) -> 'ARCProgram':
        """
        Create program from v0.94-style pattern.
        
        Args:
            pattern: List like ['rotate(angle=90)', 'filter_color(color=2)']
        
        Returns:
            ARCProgram instance
        """
        operations = []
        
        for item in pattern:
            if '(' in item:
                # Parametric: 'rotate(angle=90)'
                op_name = item[:item.index('(')]
                param_str = item[item.index('(')+1:item.index(')')]
                
                params = {}
                if param_str:
                    for pair in param_str.split(','):
                        k, v = pair.split('=')
                        # Try to parse value as int, float, or string
                        try:
                            v = int(v)
                        except ValueError:
                            try:
                                v = float(v)
                            except ValueError:
                                pass  # Keep as string
                        params[k.strip()] = v
                
                operations.append((op_name, params))
            else:
                # Non-parametric: 'transpose'
                operations.append((item, {}))
        
        return ARCProgram(operations)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            'operations': [
                {'name': op, 'params': params}
                for op, params in self.operations
            ]
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'ARCProgram':
        """Deserialize from dictionary"""
        operations = [
            (op_data['name'], op_data['params'])
            for op_data in data['operations']
        ]
        return ARCProgram(operations)
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict())
    
    @staticmethod
    def from_json(json_str: str) -> 'ARCProgram':
        """Deserialize from JSON string"""
        return ARCProgram.from_dict(json.loads(json_str))
    
    def __len__(self) -> int:
        """Return number of operations"""
        return len(self.operations)
    
    def __str__(self) -> str:
        """String representation"""
        return ' -> '.join(self.to_pattern())
    
    def __repr__(self) -> str:
        """Debug representation"""
        return f"ARCProgram({self.operations})"
    
    def __eq__(self, other: 'ARCProgram') -> bool:
        """Check equality"""
        if not isinstance(other, ARCProgram):
            return False
        return self.operations == other.operations
    
    def __hash__(self) -> int:
        """Make hashable (for use in sets/dicts)"""
        return hash(tuple(
            (op, tuple(sorted(params.items())))
            for op, params in self.operations
        ))


def test_arc_program():
    """Test ARCProgram functionality"""
    print("Testing ARCProgram...")
    
    # Test 1: Create and execute simple program
    program = ARCProgram([
        ('rotate', {'angle': 90}),
        ('filter_color', {'color': 2})
    ])
    
    print(f"Program: {program}")
    print(f"Pattern: {program.to_pattern()}")
    print(f"Length: {len(program)}")
    
    # Test 2: Serialization
    json_str = program.to_json()
    print(f"JSON: {json_str}")
    
    program2 = ARCProgram.from_json(json_str)
    assert program == program2, "Serialization failed"
    print("Serialization: OK")
    
    # Test 3: Pattern conversion
    pattern = ['rotate(angle=90)', 'filter_color(color=2)', 'border']
    program3 = ARCProgram.from_pattern(pattern)
    print(f"From pattern: {program3}")
    assert len(program3) == 3, "Pattern parsing failed"
    print("Pattern parsing: OK")
    
    # Test 4: Copy
    program4 = program.copy()
    program4.add_operation('transpose', {})
    assert len(program4) == 3, "Copy failed"
    assert len(program) == 2, "Copy modified original"
    print("Copy: OK")
    
    # Test 5: Execution (mock operation map)
    operation_map = {
        'rotate': lambda grid, angle: np.rot90(grid, k=angle//90),
        'filter_color': lambda grid, color: np.where(grid == color, color, 0)
    }
    
    test_grid = np.array([[1, 2], [3, 2]])
    result = program.execute(test_grid, operation_map)
    print(f"Execution result shape: {result.shape}")
    print("Execution: OK")
    
    print("All tests passed!")


if __name__ == "__main__":
    test_arc_program()
