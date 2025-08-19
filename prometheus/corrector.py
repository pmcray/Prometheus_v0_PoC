

import logging
from .reloader import reload_agent_module

class CorrectorAgent:
    def correct(self, original_code, failed_code, critique):
        """
        Generates a new prompt for the CoderAgent based on the critique.
        This is part of the standard CRLS loop.
        """
        critique_reason = str(critique)
        logging.info(f"CorrectorAgent: Received critique - {critique_reason}")
        
        prompt = f"""The previous attempt to refactor the code failed.
        
Original Code:
```python
{original_code}
```

Failed Code:
```python
{failed_code}
```

Causal Critique: {critique_reason}

Please try again to refactor the code, taking the critique into account.
The goal is to improve the time complexity of the code.
"""
        logging.info("CorrectorAgent: Created new instruction for CoderAgent.")
        return prompt

    def trigger_self_modification(self, module_name: str, patch_is_verified: bool):
        """
        Triggers the dynamic reloading of a module after a patch has been
        successfully verified by the Introspection and Evaluation Engine (IEE).

        Args:
            module_name: The name of the module to be reloaded (e.g., 'prometheus.coder').
            patch_is_verified: A boolean flag from the IEE confirming the patch is safe.

        Returns:
            True if the reload was successful, False otherwise.
        """
        if not patch_is_verified:
            logging.warning("CorrectorAgent: Self-modification aborted. Patch was not verified by IEE.")
            return False

        logging.info(f"CorrectorAgent: IEE confirmed patch verification. Triggering hot-swap for module: {module_name}")

        success = reload_agent_module(module_name)

        if success:
            logging.info(f"CorrectorAgent: Successfully triggered reload for {module_name}.")
        else:
            logging.error(f"CorrectorAgent: Failed to trigger reload for {module_name}.")

        return success
