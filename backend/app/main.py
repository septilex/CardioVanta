from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import logging
from backend.app.core.config import settings
from backend.app.core.model_loader import ModelLoader
from src.inference.predict import InferenceEngine
from backend.app.api.endpoints import predict
from backend.app.core.logging import setup_logging
from backend.app.api.middleware import MonitoringMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request

setup_logging()
logger = logging.getLogger(__name__)

# Global state for the application
model_package = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_package
    logger.info("Starting up CardioVanta API...")
    try:
        loader = ModelLoader(model_dir=settings.MODEL_DIR)
        model_package = loader.load_and_validate()
        
        # Instantiate InferenceEngine and bypass its disk loading
        engine = InferenceEngine(model_dir=settings.MODEL_DIR)
        engine.model = model_package.model
        engine.explanation_model = model_package.explanation_model
        engine.schema = model_package.feature_schema
        engine.metadata = model_package.metadata
        app.state.inference_engine = engine
        
        logger.info("Startup validation complete. CardioVanta Core Runtime ready.")
    except Exception as e:
        logger.error(f"Startup validation failed: {e}")
        # Fail clearly on startup
        raise RuntimeError(f"Startup validation failed: {e}")
    
    yield
    
    logger.info("Shutting down CardioVanta API...")
    model_package = None
    app.state.inference_engine = None

from fastapi.middleware.cors import CORSMiddleware
 
docs_url = "/docs" if settings.ENABLE_DOCS else None
redoc_url = "/redoc" if settings.ENABLE_DOCS else None
openapi_url = "/openapi.json" if settings.ENABLE_DOCS else None

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(MonitoringMiddleware)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", None)
    logger.error("Validation error", extra={
        "request_id": req_id,
        "status_code": 422,
        "endpoint": request.url.path,
        "errors": exc.errors()
    })
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", None)
    logger.error(f"HTTP exception: {exc.detail}", extra={
        "request_id": req_id,
        "status_code": exc.status_code,
        "endpoint": request.url.path
    })
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

app.include_router(predict.router, prefix="/api/v1", tags=["predict"])

@app.get("/api/v1/health")
def health_check():
    """Minimal health check for Stage 1. Does not expose sensitive metadata."""
    if model_package is None:
        raise HTTPException(status_code=503, detail="Service Unavailable: Model package not loaded")
    return {"status": "ok", "service": "CardioVanta"}
