import logging
import json
import uuid
import os

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        if hasattr(record, 'extra_data'):
            log_record.update(record.extra_data)
        return json.dumps(log_record)

def setup_logging():
    run_id = str(uuid.uuid4())
    log_dir = "run_logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, f"run-{run_id}.jsonl")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove all existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create a file handler for the run-specific log file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    # Create a stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)

    return run_id
