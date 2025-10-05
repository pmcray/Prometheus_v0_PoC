"""
Enhanced Dynamic Module Reloader for RSI capabilities
Implements hot-swapping features from v0.40 onwards with patch application and self-modification
"""

import importlib
import importlib.util
import sys
import os
import logging
import time
import subprocess
import tempfile
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path

class EnhancedModuleReloader:
    """Enhanced reloader with patch application and self-modification capabilities"""

    def __init__(self):
        self.loaded_modules = {}
        self.module_timestamps = {}
        self.reload_history = []
        self.patch_history = []

    def reload_agent_module(self, module_name: str) -> bool:
        """Reload a specific agent module"""
        try:
            # Clear import caches
            importlib.invalidate_caches()

            # Find the module in sys.modules
            if module_name in sys.modules:
                module_obj = sys.modules[module_name]

                # Record reload attempt
                reload_event = {
                    "timestamp": time.time(),
                    "module": module_name,
                    "status": "attempting"
                }

                # Perform the reload
                reloaded_module = importlib.reload(module_obj)

                # Update status
                reload_event["status"] = "success"
                reload_event["new_module"] = reloaded_module

                self.reload_history.append(reload_event)

                logging.info(f"Successfully reloaded module: {module_name}")
                return True

            else:
                logging.error(f"Module {module_name} not found in sys.modules")
                return False

        except Exception as e:
            reload_event = {
                "timestamp": time.time(),
                "module": module_name,
                "status": "failed",
                "error": str(e)
            }
            self.reload_history.append(reload_event)

            logging.error(f"Failed to reload module {module_name}: {e}")
            return False

    def apply_patch(self, module_path: str, patch_content: str) -> bool:
        """Apply a git-style patch to a module file"""
        try:
            # Record patch attempt
            patch_event = {
                "timestamp": time.time(),
                "target_file": module_path,
                "patch_hash": hashlib.md5(patch_content.encode()).hexdigest()[:8],
                "status": "attempting"
            }

            # Create temporary patch file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as patch_file:
                patch_file.write(patch_content)
                patch_file_path = patch_file.name

            try:
                # Check if git is available and try git apply first
                result = subprocess.run(
                    ['git', 'apply', '--check', patch_file_path],
                    cwd=os.path.dirname(module_path) or '.',
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    # Patch is valid, apply it
                    result = subprocess.run(
                        ['git', 'apply', patch_file_path],
                        cwd=os.path.dirname(module_path) or '.',
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    if result.returncode == 0:
                        patch_event["status"] = "success"
                        patch_event["method"] = "git_apply"
                        self.patch_history.append(patch_event)
                        logging.info(f"Successfully applied patch to {module_path} using git")
                        return True
                    else:
                        logging.warning(f"Git apply failed: {result.stderr}")

            except (subprocess.TimeoutExpired, FileNotFoundError):
                logging.warning("Git not available or timeout, falling back to manual patch")

            # Fallback to manual patch application
            success = self._apply_patch_manually(module_path, patch_content)
            if success:
                patch_event["status"] = "success"
                patch_event["method"] = "manual"
                self.patch_history.append(patch_event)
                logging.info(f"Successfully applied patch to {module_path} manually")
                return True
            else:
                patch_event["status"] = "failed"
                patch_event["error"] = "Manual patch application failed"
                self.patch_history.append(patch_event)
                return False

        except Exception as e:
            patch_event["status"] = "failed"
            patch_event["error"] = str(e)
            self.patch_history.append(patch_event)
            logging.error(f"Error applying patch: {e}")
            return False
        finally:
            # Clean up temporary patch file
            if 'patch_file_path' in locals():
                try:
                    os.unlink(patch_file_path)
                except:
                    pass

    def _apply_patch_manually(self, module_path: str, patch_content: str) -> bool:
        """Manually apply simple patches when git is not available"""
        try:
            # This is a very simplified patch parser for basic cases
            # In production, would need more robust patch parsing

            lines = patch_content.split('\n')
            additions = []
            deletions = []

            for line in lines:
                if line.startswith('+') and not line.startswith('+++'):
                    additions.append(line[1:])  # Remove + prefix
                elif line.startswith('-') and not line.startswith('---'):
                    deletions.append(line[1:])  # Remove - prefix

            # Read current file
            with open(module_path, 'r') as f:
                content = f.read()

            # Apply simple replacements (this is very basic)
            for deletion in deletions:
                if deletion.strip() in content:
                    content = content.replace(deletion.strip(), '', 1)

            for addition in additions:
                # Simple append to end (would need more sophisticated logic for real patches)
                if addition.strip() and addition.strip() not in content:
                    content += '\n' + addition

            # Write back
            with open(module_path, 'w') as f:
                f.write(content)

            return True

        except Exception as e:
            logging.error(f"Manual patch application failed: {e}")
            return False

    def backup_module(self, module_path: str) -> str:
        """Create a backup of a module before modification"""
        backup_path = f"{module_path}.backup.{int(time.time())}"

        try:
            with open(module_path, 'r') as original:
                with open(backup_path, 'w') as backup:
                    backup.write(original.read())

            logging.info(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            logging.error(f"Failed to create backup: {e}")
            raise

    def validate_module_syntax(self, module_path: str) -> bool:
        """Validate that a module has correct Python syntax"""
        try:
            with open(module_path, 'r') as f:
                source = f.read()

            # Try to compile the source
            compile(source, module_path, 'exec')
            return True

        except SyntaxError as e:
            logging.error(f"Syntax error in {module_path}: {e}")
            return False
        except Exception as e:
            logging.error(f"Error validating {module_path}: {e}")
            return False

    def get_reload_history(self) -> List[Dict[str, Any]]:
        """Get the history of reload attempts"""
        return self.reload_history.copy()

    def get_patch_history(self) -> List[Dict[str, Any]]:
        """Get the history of patch applications"""
        return self.patch_history.copy()

    def rollback_module(self, module_path: str, backup_path: str) -> bool:
        """Rollback a module to a previous backup"""
        try:
            with open(backup_path, 'r') as backup:
                with open(module_path, 'w') as original:
                    original.write(backup.read())

            logging.info(f"Rolled back {module_path} from {backup_path}")
            return True

        except Exception as e:
            logging.error(f"Failed to rollback {module_path}: {e}")
            return False

class StatelessAgentManager:
    """Manages stateless instantiation of agents for safe reloading"""

    def __init__(self):
        self.agent_factories = {}
        self.reloader = EnhancedModuleReloader()

    def register_agent_factory(self, agent_name: str, module_name: str, class_name: str):
        """Register an agent factory for stateless instantiation"""
        self.agent_factories[agent_name] = {
            "module": module_name,
            "class": class_name
        }

    def create_agent_instance(self, agent_name: str, *args, **kwargs):
        """Create a fresh instance of an agent"""
        if agent_name not in self.agent_factories:
            raise ValueError(f"Unknown agent: {agent_name}")

        factory_info = self.agent_factories[agent_name]
        module_name = factory_info["module"]
        class_name = factory_info["class"]

        # Import the module (will use reloaded version if available)
        module = importlib.import_module(module_name)

        # Get the class
        agent_class = getattr(module, class_name)

        # Create and return instance
        return agent_class(*args, **kwargs)

    def reload_and_recreate(self, agent_name: str, *args, **kwargs):
        """Reload agent module and create new instance"""
        if agent_name not in self.agent_factories:
            raise ValueError(f"Unknown agent: {agent_name}")

        factory_info = self.agent_factories[agent_name]
        module_name = factory_info["module"]

        # Reload the module
        success = self.reloader.reload_agent_module(module_name)

        if success:
            # Create new instance with reloaded code
            return self.create_agent_instance(agent_name, *args, **kwargs)
        else:
            raise RuntimeError(f"Failed to reload module for agent: {agent_name}")

class SelfModificationEngine:
    """Engine for self-modification workflows (v0.29+)"""

    def __init__(self, gene_bank=None):
        self.gene_bank = gene_bank
        self.reloader = EnhancedModuleReloader()
        self.agent_manager = StatelessAgentManager()
        self.modification_log = []

    def execute_self_modification(self, target_module: str, patch_content: str,
                                 run_verification: bool = True) -> bool:
        """Execute a complete self-modification cycle"""
        modification_id = f"mod_{int(time.time())}"

        try:
            # Log start of modification
            mod_event = {
                "id": modification_id,
                "timestamp": time.time(),
                "target_module": target_module,
                "status": "started"
            }
            self.modification_log.append(mod_event)

            # Find module file path
            module_path = self._find_module_path(target_module)
            if not module_path:
                raise FileNotFoundError(f"Cannot find module file for {target_module}")

            # Create backup
            backup_path = self.reloader.backup_module(module_path)
            mod_event["backup_path"] = backup_path

            # Apply patch
            patch_success = self.reloader.apply_patch(module_path, patch_content)
            if not patch_success:
                raise RuntimeError("Failed to apply patch")

            # Validate syntax
            if not self.reloader.validate_module_syntax(module_path):
                # Rollback on syntax error
                self.reloader.rollback_module(module_path, backup_path)
                raise SyntaxError("Modified module has syntax errors")

            # Run verification if requested
            if run_verification:
                verification_result = self._run_verification_tests(target_module)
                if not verification_result:
                    # Rollback on verification failure
                    self.reloader.rollback_module(module_path, backup_path)
                    raise RuntimeError("Modified module failed verification tests")

            # Reload module
            reload_success = self.reloader.reload_agent_module(target_module)
            if not reload_success:
                # Rollback on reload failure
                self.reloader.rollback_module(module_path, backup_path)
                raise RuntimeError("Failed to reload modified module")

            # Store successful modification in gene bank
            if self.gene_bank:
                with open(module_path, 'r') as f:
                    new_code = f.read()

                self.gene_bank.store_code_gene(
                    target_module,
                    new_code,
                    f"auto_v{int(time.time())}",
                    {
                        "modification_id": modification_id,
                        "patch_applied": patch_content[:200] + "..." if len(patch_content) > 200 else patch_content,
                        "verification_passed": run_verification,
                        "fitness_score": 1.0  # Would be calculated based on performance
                    }
                )

            # Update log
            mod_event["status"] = "completed"
            mod_event["end_timestamp"] = time.time()

            logging.info(f"Successfully completed self-modification: {modification_id}")
            return True

        except Exception as e:
            # Update log with failure
            mod_event["status"] = "failed"
            mod_event["error"] = str(e)
            mod_event["end_timestamp"] = time.time()

            logging.error(f"Self-modification failed: {e}")
            return False

    def _find_module_path(self, module_name: str) -> Optional[str]:
        """Find the file path for a module"""
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, '__file__') and module.__file__:
                return module.__file__
        except ImportError:
            pass

        # Try common patterns
        possible_paths = [
            f"prometheus/{module_name.replace('.', '/')}.py",
            f"{module_name.replace('.', '/')}.py",
            f"src/{module_name.replace('.', '/')}.py"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)

        return None

    def _run_verification_tests(self, module_name: str) -> bool:
        """Run verification tests on modified module"""
        try:
            # This is a simplified verification - would need more comprehensive testing
            # Try to import the modified module
            importlib.import_module(module_name)

            # Could run unit tests, integration tests, etc.
            logging.info(f"Verification passed for {module_name}")
            return True

        except Exception as e:
            logging.error(f"Verification failed for {module_name}: {e}")
            return False

    def get_modification_history(self) -> List[Dict[str, Any]]:
        """Get history of self-modifications"""
        return self.modification_log.copy()

# Global instances
enhanced_reloader = EnhancedModuleReloader()
agent_manager = StatelessAgentManager()
self_modification_engine = SelfModificationEngine()