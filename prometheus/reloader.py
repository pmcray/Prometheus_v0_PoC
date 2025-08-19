import importlib
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def reload_agent_module(module_name: str) -> bool:
    """
    Dynamically reloads a given agent module.

    Args:
        module_name: The name of the module to reload (e.g., 'prometheus.coder').

    Returns:
        True if the module was reloaded successfully, False otherwise.
    """
    try:
        # Ensure the import system notices any changes to the source file
        importlib.invalidate_caches()

        if module_name not in sys.modules:
            logging.warning(f"Module {module_name} not found in sys.modules. It may have not been imported yet.")
            # Attempt to import it
            importlib.import_module(module_name)

        module_object = sys.modules[module_name]

        logging.info(f"Attempting to reload module: {module_name}")
        importlib.reload(module_object)
        logging.info(f"Successfully reloaded module: {module_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to reload module {module_name}: {e}", exc_info=True)
        return False
