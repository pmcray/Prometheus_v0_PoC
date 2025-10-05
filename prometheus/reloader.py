#!/usr/bin/env python3
"""
Dynamic Module Reloader for Project Prometheus v0.40
Implements lightweight dynamic module reloading for self-modification
"""

import importlib
import logging
import sys
import traceback
from typing import Optional, Any, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

class ModuleReloadError(Exception):
    """Exception raised when module reloading fails"""
    pass

class ModuleReloader:
    """
    Handles safe dynamic reloading of Python modules for self-modification.
    Designed to support the stateless agent instantiation pattern.
    """

    def __init__(self):
        self.reload_history: Dict[str, int] = {}
        self.failed_reloads: Dict[str, str] = {}

    def reload_agent_module(self, module_name: str) -> bool:
        """
        Safely reload a module with comprehensive error handling.

        Args:
            module_name: Name of the module to reload (e.g., 'prometheus.coder')

        Returns:
            bool: True if reload successful, False otherwise
        """
        logger.info(f"Attempting to reload module: {module_name}")

        try:
            # Clear import system caches to ensure fresh file read
            importlib.invalidate_caches()
            logger.debug("Cleared importlib caches")

            # Check if module exists in sys.modules
            if module_name not in sys.modules:
                logger.warning(f"Module {module_name} not found in sys.modules")
                return False

            # Get module object
            module_object = sys.modules[module_name]

            # Perform the reload
            reloaded_module = importlib.reload(module_object)

            # Update reload history
            self.reload_history[module_name] = self.reload_history.get(module_name, 0) + 1

            # Clear any previous failure record
            if module_name in self.failed_reloads:
                del self.failed_reloads[module_name]

            logger.info(f"Successfully reloaded {module_name} "
                       f"(reload count: {self.reload_history[module_name]})")
            return True

        except SyntaxError as e:
            error_msg = f"Syntax error in {module_name}: {e}"
            logger.error(error_msg)
            self.failed_reloads[module_name] = error_msg
            return False

        except ImportError as e:
            error_msg = f"Import error in {module_name}: {e}"
            logger.error(error_msg)
            self.failed_reloads[module_name] = error_msg
            return False

        except Exception as e:
            error_msg = f"Unexpected error reloading {module_name}: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.failed_reloads[module_name] = error_msg
            return False

    def get_reload_status(self, module_name: str) -> Dict[str, Any]:
        """
        Get detailed reload status for a module.

        Args:
            module_name: Name of the module

        Returns:
            Dict containing reload count, last error, etc.
        """
        return {
            'module_name': module_name,
            'reload_count': self.reload_history.get(module_name, 0),
            'last_error': self.failed_reloads.get(module_name, None),
            'is_loaded': module_name in sys.modules
        }

    def verify_module_file_exists(self, module_name: str) -> bool:
        """
        Verify that the module file exists on disk.

        Args:
            module_name: Name of the module

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            # Convert module name to file path
            module_path = module_name.replace('.', '/')

            # Check for .py file
            py_file = Path(f"{module_path}.py")
            if py_file.exists():
                logger.debug(f"Found module file: {py_file}")
                return True

            # Check for __init__.py in package directory
            init_file = Path(f"{module_path}/__init__.py")
            if init_file.exists():
                logger.debug(f"Found package init file: {init_file}")
                return True

            logger.warning(f"Module file not found for: {module_name}")
            return False

        except Exception as e:
            logger.error(f"Error checking module file for {module_name}: {e}")
            return False

    def get_reload_history(self) -> Dict[str, int]:
        """Get complete reload history for all modules."""
        return self.reload_history.copy()

    def get_failed_reloads(self) -> Dict[str, str]:
        """Get history of failed reload attempts."""
        return self.failed_reloads.copy()

    def reset_history(self):
        """Reset reload history (for testing purposes)."""
        self.reload_history.clear()
        self.failed_reloads.clear()
        logger.info("Reset module reload history")

# Global reloader instance
_global_reloader = ModuleReloader()

def reload_agent_module(module_name: str) -> bool:
    """
    Convenience function for reloading a module.
    Uses global reloader instance.

    Args:
        module_name: Name of the module to reload

    Returns:
        bool: True if reload successful, False otherwise
    """
    return _global_reloader.reload_agent_module(module_name)

def get_reload_status(module_name: str) -> Dict[str, Any]:
    """Get reload status using global reloader instance."""
    return _global_reloader.get_reload_status(module_name)

def get_global_reloader() -> ModuleReloader:
    """Get the global reloader instance."""
    return _global_reloader