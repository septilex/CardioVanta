import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

logger = logging.getLogger(__name__)

class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        request.state.start_time = start_time
        
        try:
            response = await call_next(request)
            process_time_ms = (time.time() - start_time) * 1000
            
            # Note: We don't log successful requests here because the endpoint 
            # will log the detailed domain-specific prediction event.
            # We can log non-200s or non-/predict here if desired, but 
            # the design says exceptions are handled by exception handlers.
            return response
            
        except Exception as e:
            process_time_ms = (time.time() - start_time) * 1000
            logger.error(f"Unhandled exception in middleware: {type(e).__name__}", extra={
                "request_id": request_id,
                "latency_ms": process_time_ms,
                "status_code": 500,
                "endpoint": request.url.path
            })
            raise e
