import json
import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PerformanceLogger:
    """Enhanced performance logging"""

    def __init__(self, log_file: str = "performance_log_v0.18.json"):
        self.log_file = log_file
        self.performance_data = []

    def log_action(self, agent_name: str, action: str, cost: int, success: bool, details: Dict[str, Any]):
        entry = {
            'timestamp': time.time(),
            'agent': agent_name,
            'action': action,
            'cost': cost,
            'success': success,
            'details': details
        }
        self.performance_data.append(entry)

        with open(self.log_file, 'w') as f:
            json.dump(self.performance_data, f, indent=2)

        logger.info(f"📝 Logged: {agent_name} - {action} (Cost: {cost}, Success: {success})")
