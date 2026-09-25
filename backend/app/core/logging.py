import json
import logging
import traceback
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
        }
        
        # Extract fields from record.__dict__ that are not standard LogRecord attributes
        standard_attrs = {
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
            'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
            'msecs', 'message', 'msg', 'name', 'pathname', 'process',
            'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName',
            'taskName'
        }
        
        extra_attrs = {k: v for k, v in record.__dict__.items() if k not in standard_attrs}
        log_record.update(extra_attrs)
            
        if record.exc_info:
            log_record["exception"] = "".join(traceback.format_exception(*record.exc_info))
            
        return json.dumps(log_record)

def setup_logging():
    logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    import sys
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Configure uvicorn loggers to use JSON format as well
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers = [handler]
        uv_logger.propagate = False
